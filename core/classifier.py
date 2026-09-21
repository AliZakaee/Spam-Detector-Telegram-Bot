"""Spam classifiers: local SVM, TypeSafe Jev, or both."""

import logging
import os
from dataclasses import dataclass

import joblib
from typesafe_sdk import TypeSafeClient

from core.config import DEFAULT_CONFIDENCE_FLOOR, DEFAULT_SPAM_THRESHOLD
from core.typesafe_moderation import SPAM_QUESTIONS, build_moderation_state, route_typesafe_answers
from preprocessing import normalize_text


@dataclass(frozen=True)
class ClassificationResult:
    label: str
    spam_confidence: float
    source: str
    should_flag: bool
    reasons: tuple = ()
    choice_confidence: float = None
    hazards: dict = None
    severity: float = None
    error: str = None


def _fail_open(source, error, logger=None):
    if logger is not None:
        logger.error("Classification failed (%s); failing open. %s", source, error)
    return ClassificationResult(
        label="normal",
        spam_confidence=0.0,
        source=source,
        should_flag=False,
        error=str(error),
    )


class SvmClassifier:
    name = "svm"

    def __init__(self, model, vectorizer, spam_index, spam_threshold=DEFAULT_SPAM_THRESHOLD):
        self.model = model
        self.vectorizer = vectorizer
        self.spam_index = spam_index
        self.spam_threshold = spam_threshold

    def describe(self):
        return "Local TF-IDF + linear SVM trained from your CSV."

    def classify(self, text):
        features = self.vectorizer.transform([normalize_text(text)])
        probabilities = self.model.predict_proba(features)[0]
        spam_confidence = float(probabilities[self.spam_index])
        label = str(self.model.classes_[probabilities.argmax()])
        should_flag = label == "spam" and spam_confidence > self.spam_threshold
        return ClassificationResult(
            label=label,
            spam_confidence=spam_confidence,
            source=self.name,
            should_flag=should_flag,
        )


class TypeSafeClassifier:
    name = "typesafe"

    def __init__(
        self,
        client,
        spam_threshold=DEFAULT_SPAM_THRESHOLD,
        confidence_floor=DEFAULT_CONFIDENCE_FLOOR,
        logger=None,
    ):
        self.client = client
        self.spam_threshold = spam_threshold
        self.confidence_floor = confidence_floor
        self.logger = logger or logging.getLogger(__name__)

    def describe(self):
        return "TypeSafe Jev — structured spam judgments, no local training required."

    def classify(self, text):
        try:
            response = self.client.system_one(
                state=build_moderation_state(text),
                questions=SPAM_QUESTIONS,
            )
            routed = route_typesafe_answers(
                response.answers,
                spam_threshold=self.spam_threshold,
                confidence_floor=self.confidence_floor,
            )
        except Exception as exc:
            return _fail_open(self.name, exc, self.logger)
        return ClassificationResult(source=self.name, **routed)


class HybridClassifier:
    name = "hybrid"

    def __init__(self, typesafe_classifier, svm_classifier, logger=None):
        self.typesafe_classifier = typesafe_classifier
        self.svm_classifier = svm_classifier
        self.logger = logger or logging.getLogger(__name__)

    def describe(self):
        return (
            "TypeSafe Jev plus the local SVM. Either side can flag a message for review; "
            "if TypeSafe is unavailable the SVM is used alone."
        )

    def classify(self, text):
        svm_result = self.svm_classifier.classify(text)
        typesafe_result = self.typesafe_classifier.classify(text)
        if typesafe_result.error:
            self.logger.error(
                "TypeSafe failed in hybrid mode; using SVM. %s",
                typesafe_result.error,
            )
            return ClassificationResult(
                label=svm_result.label,
                spam_confidence=svm_result.spam_confidence,
                source=self.name,
                should_flag=svm_result.should_flag,
                error=typesafe_result.error,
            )
        return merge_hybrid(typesafe_result, svm_result)


def merge_hybrid(typesafe_result, svm_result):
    """OR the two judges: this bot queues for admin review, so missed spam is costlier."""
    should_flag = typesafe_result.should_flag or svm_result.should_flag
    spam_confidence = max(typesafe_result.spam_confidence, svm_result.spam_confidence)
    if typesafe_result.label == "spam" or svm_result.label == "spam":
        label = "spam"
    else:
        label = "normal"

    reasons = list(typesafe_result.reasons)
    if svm_result.should_flag and not typesafe_result.should_flag:
        reasons.append("مدل محلی SVM")

    return ClassificationResult(
        label=label,
        spam_confidence=spam_confidence,
        source="hybrid",
        should_flag=should_flag,
        reasons=tuple(reasons),
        choice_confidence=typesafe_result.choice_confidence,
        hazards=typesafe_result.hazards,
        severity=typesafe_result.severity,
        error=typesafe_result.error,
    )


def svm_artifacts_exist(model_path, vectorizer_path):
    return os.path.isfile(model_path) and os.path.isfile(vectorizer_path)


def load_svm_classifier(model_path, vectorizer_path, spam_threshold=DEFAULT_SPAM_THRESHOLD):
    try:
        model = joblib.load(model_path)
        vectorizer = joblib.load(vectorizer_path)
    except (FileNotFoundError, OSError) as exc:
        raise SystemExit(
            f"Could not load model/vectorizer ({exc}). Run 'python train/train.py' first."
        ) from exc

    try:
        spam_index = list(model.classes_).index("spam")
    except ValueError as exc:
        raise SystemExit(
            "Loaded model has no 'spam' class. Retrain with a dataset that contains 'spam' labels."
        ) from exc

    return SvmClassifier(model, vectorizer, spam_index, spam_threshold=spam_threshold)


def resolve_backend(requested, has_typesafe, has_svm):
    """Pick an actual backend from CLASSIFIER_BACKEND plus what is configured."""
    if requested == "auto":
        if has_typesafe and has_svm:
            return "hybrid"
        if has_typesafe:
            return "typesafe"
        if has_svm:
            return "svm"
        raise SystemExit(
            "No classifier is configured. Set TYPESAFE_API_KEY to use TypeSafe without training, "
            "or run 'python train/train.py' to build model.pkl and vectorizer.pkl."
        )

    if requested == "typesafe":
        if not has_typesafe:
            raise SystemExit("CLASSIFIER_BACKEND=typesafe requires TYPESAFE_API_KEY.")
        return "typesafe"

    if requested == "svm":
        if not has_svm:
            raise SystemExit(
                "CLASSIFIER_BACKEND=svm requires model.pkl and vectorizer.pkl. "
                "Run 'python train/train.py' first, or set TYPESAFE_API_KEY to use TypeSafe."
            )
        return "svm"

    if requested == "hybrid":
        if has_typesafe and has_svm:
            return "hybrid"
        if has_typesafe:
            return "typesafe"
        if has_svm:
            return "svm"
        raise SystemExit(
            "CLASSIFIER_BACKEND=hybrid needs TYPESAFE_API_KEY and/or a trained SVM."
        )

    raise SystemExit(f"Unknown classifier backend: {requested!r}.")


def build_classifier(
    backend,
    model_path,
    vectorizer_path,
    typesafe_api_key=None,
    spam_threshold=DEFAULT_SPAM_THRESHOLD,
    confidence_floor=DEFAULT_CONFIDENCE_FLOOR,
    logger=None,
    typesafe_client=None,
):
    has_typesafe = bool(typesafe_api_key and str(typesafe_api_key).strip()) or typesafe_client is not None
    has_svm = svm_artifacts_exist(model_path, vectorizer_path)
    resolved = resolve_backend(backend, has_typesafe, has_svm)
    logger = logger or logging.getLogger(__name__)

    svm_classifier = None
    if resolved in ("svm", "hybrid"):
        svm_classifier = load_svm_classifier(model_path, vectorizer_path, spam_threshold=spam_threshold)

    typesafe_classifier = None
    if resolved in ("typesafe", "hybrid"):
        client = typesafe_client or TypeSafeClient(api_key=typesafe_api_key, timeout=20.0)
        typesafe_classifier = TypeSafeClassifier(
            client,
            spam_threshold=spam_threshold,
            confidence_floor=confidence_floor,
            logger=logger,
        )

    if resolved == "hybrid":
        return HybridClassifier(typesafe_classifier, svm_classifier, logger=logger)
    if resolved == "typesafe":
        return typesafe_classifier
    return svm_classifier
