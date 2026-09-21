import math


DEFAULT_SPAM_THRESHOLD = 0.4
DEFAULT_CONFIDENCE_FLOOR = 0.5
DEFAULT_CLASSIFIER_BACKEND = "auto"
VALID_CLASSIFIER_BACKENDS = frozenset({"auto", "typesafe", "svm", "hybrid"})


def parse_unit_interval(value, default):
    """Return a finite 0–1 float, or `default` when the value is unusable."""
    try:
        number = float(value)
    except (TypeError, ValueError):
        return default

    if not math.isfinite(number) or not 0 <= number <= 1:
        return default
    return number


def parse_spam_threshold(value):
    """Return a valid probability threshold, falling back to the safe default."""
    return parse_unit_interval(value, DEFAULT_SPAM_THRESHOLD)


def parse_confidence_floor(value):
    """Return a valid TypeSafe confidence floor, falling back to the safe default."""
    return parse_unit_interval(value, DEFAULT_CONFIDENCE_FLOOR)


def parse_classifier_backend(value):
    """Return a normalized backend name, or raise for an unknown value."""
    if value is None or str(value).strip() == "":
        return DEFAULT_CLASSIFIER_BACKEND
    normalized = str(value).strip().lower()
    if normalized not in VALID_CLASSIFIER_BACKENDS:
        allowed = ", ".join(sorted(VALID_CLASSIFIER_BACKENDS))
        raise ValueError(f"CLASSIFIER_BACKEND must be one of: {allowed}. Got {value!r}.")
    return normalized
