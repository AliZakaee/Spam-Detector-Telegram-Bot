import os
import tempfile
import unittest
from types import SimpleNamespace
from unittest.mock import Mock

from sklearn.feature_extraction.text import TfidfVectorizer
from sklearn.svm import SVC

from core.classifier import (
    ClassificationResult,
    HybridClassifier,
    SvmClassifier,
    TypeSafeClassifier,
    build_classifier,
    merge_hybrid,
    resolve_backend,
)
from core.classification_text import format_admin_alert, format_check_reply, format_status


def _tiny_svm(spam_threshold=0.4):
    texts = ["buy crypto now t.me/spam"] * 6 + ["hello how are you today"] * 6
    labels = ["spam"] * 6 + ["normal"] * 6
    vectorizer = TfidfVectorizer()
    features = vectorizer.fit_transform(texts)
    model = SVC(kernel="linear", probability=True)
    model.fit(features, labels)
    return SvmClassifier(
        model,
        vectorizer,
        list(model.classes_).index("spam"),
        spam_threshold=spam_threshold,
    )


def _typesafe_result(**overrides):
    values = dict(
        label="normal",
        spam_confidence=0.05,
        source="typesafe",
        should_flag=False,
        reasons=(),
        choice_confidence=0.9,
        hazards={"unsolicited_ad": 0.02},
        severity=0.1,
        error=None,
    )
    values.update(overrides)
    return ClassificationResult(**values)


class ResolveBackendTests(unittest.TestCase):
    def test_auto_prefers_hybrid_when_both_are_available(self):
        self.assertEqual(resolve_backend("auto", True, True), "hybrid")

    def test_auto_uses_typesafe_without_training(self):
        self.assertEqual(resolve_backend("auto", True, False), "typesafe")

    def test_auto_uses_svm_without_api_key(self):
        self.assertEqual(resolve_backend("auto", False, True), "svm")

    def test_auto_with_neither_exits(self):
        with self.assertRaises(SystemExit):
            resolve_backend("auto", False, False)

    def test_hybrid_degrades_when_only_one_side_exists(self):
        self.assertEqual(resolve_backend("hybrid", True, False), "typesafe")
        self.assertEqual(resolve_backend("hybrid", False, True), "svm")

    def test_explicit_typesafe_requires_key(self):
        with self.assertRaises(SystemExit):
            resolve_backend("typesafe", False, True)


class SvmClassifierTests(unittest.TestCase):
    def test_flags_lexical_spam_and_passes_ordinary_text(self):
        classifier = _tiny_svm()
        spam = classifier.classify("buy crypto now t.me/spam")
        ham = classifier.classify("hello how are you today")

        self.assertEqual(spam.source, "svm")
        self.assertEqual(spam.label, "spam")
        self.assertTrue(spam.should_flag)
        self.assertEqual(ham.label, "normal")
        self.assertFalse(ham.should_flag)


class TypeSafeClassifierTests(unittest.TestCase):
    def test_routes_client_answers(self):
        client = Mock()
        client.system_one.return_value = SimpleNamespace(
            answers={
                "verdict": SimpleNamespace(
                    choice="spam",
                    confidence=0.95,
                    probabilities={"spam": 0.93, "normal": 0.07},
                ),
                "unsolicited_ad": SimpleNamespace(noul=0.8),
                "scam_or_phishing": SimpleNamespace(noul=0.02),
                "mass_promo_or_invite": SimpleNamespace(noul=0.1),
                "suspicious_link_or_impersonation": SimpleNamespace(noul=0.05),
                "severity": SimpleNamespace(score=2.1, confidence=0.9),
            }
        )
        classifier = TypeSafeClassifier(client, spam_threshold=0.4, confidence_floor=0.5)
        result = classifier.classify("cheap followers t.me/ads")

        self.assertEqual(result.source, "typesafe")
        self.assertTrue(result.should_flag)
        self.assertEqual(result.label, "spam")
        self.assertIn("تبلیغات ناخواسته", result.reasons)
        self.assertEqual(client.system_one.call_count, 1)
        state = client.system_one.call_args.kwargs["state"]
        self.assertEqual(state["message_text"], "cheap followers t.me/ads")

    def test_api_errors_fail_open(self):
        client = Mock()
        client.system_one.side_effect = RuntimeError("rate limited")
        classifier = TypeSafeClassifier(client, logger=Mock())

        result = classifier.classify("hello")

        self.assertFalse(result.should_flag)
        self.assertEqual(result.label, "normal")
        self.assertIn("rate limited", result.error)


class HybridClassifierTests(unittest.TestCase):
    def test_ors_independent_flags(self):
        typesafe = _typesafe_result(should_flag=False, label="normal", spam_confidence=0.1)
        svm = _typesafe_result(
            source="svm",
            should_flag=True,
            label="spam",
            spam_confidence=0.81,
            reasons=(),
            choice_confidence=None,
            hazards=None,
            severity=None,
        )
        merged = merge_hybrid(typesafe, svm)

        self.assertEqual(merged.source, "hybrid")
        self.assertTrue(merged.should_flag)
        self.assertEqual(merged.label, "spam")
        self.assertAlmostEqual(merged.spam_confidence, 0.81)
        self.assertIn("مدل محلی SVM", merged.reasons)

    def test_uses_svm_when_typesafe_errors(self):
        svm = _tiny_svm()
        failing = TypeSafeClassifier(
            Mock(system_one=Mock(side_effect=RuntimeError("down"))),
            logger=Mock(),
        )
        classifier = HybridClassifier(failing, svm, logger=Mock())

        result = classifier.classify("buy crypto now t.me/spam")

        self.assertEqual(result.source, "hybrid")
        self.assertTrue(result.should_flag)
        self.assertIn("down", result.error)


class BuildClassifierTests(unittest.TestCase):
    def test_injected_typesafe_client_avoids_training_files(self):
        client = Mock()
        client.system_one.return_value = SimpleNamespace(
            answers={
                "verdict": SimpleNamespace(
                    choice="normal",
                    confidence=1.0,
                    probabilities={"spam": 0.01, "normal": 0.99},
                ),
                "unsolicited_ad": SimpleNamespace(noul=0.0),
                "scam_or_phishing": SimpleNamespace(noul=0.0),
                "mass_promo_or_invite": SimpleNamespace(noul=0.0),
                "suspicious_link_or_impersonation": SimpleNamespace(noul=0.0),
                "severity": SimpleNamespace(score=0.0, confidence=1.0),
            }
        )
        with tempfile.TemporaryDirectory() as directory:
            classifier = build_classifier(
                backend="auto",
                model_path=os.path.join(directory, "model.pkl"),
                vectorizer_path=os.path.join(directory, "vectorizer.pkl"),
                typesafe_client=client,
            )

        self.assertEqual(classifier.name, "typesafe")
        self.assertFalse(classifier.classify("hi").should_flag)


class ClassificationTextTests(unittest.TestCase):
    def test_check_reply_includes_reasons_and_threshold_note(self):
        result = _typesafe_result(
            label="spam",
            spam_confidence=0.87,
            should_flag=True,
            reasons=("تبلیغات ناخواسته",),
            choice_confidence=0.8,
            severity=2.2,
        )
        text = format_check_reply(result)

        self.assertIn("87.00%", text)
        self.assertIn("تبلیغات ناخواسته", text)
        self.assertIn("علامت‌گذاری خودکار", text)
        self.assertIn("TypeSafe", text)

    def test_admin_alert_includes_username_and_source(self):
        result = _typesafe_result(label="spam", spam_confidence=0.5, should_flag=True)
        text = format_admin_alert(result, "@ali (`1`)")

        self.assertIn("@ali", text)
        self.assertIn("TypeSafe", text)

    def test_status_names_the_backend(self):
        classifier = SimpleNamespace(name="typesafe", describe=lambda: "TypeSafe Jev")
        text = format_status(classifier, 0.4, 0.5, "builtin")

        self.assertIn("typesafe", text)
        self.assertIn("0.4", text)
        self.assertIn("builtin", text)


if __name__ == "__main__":
    unittest.main()
