import math


DEFAULT_SPAM_THRESHOLD = 0.4


def parse_spam_threshold(value):
    """Return a valid probability threshold, falling back to the safe default."""
    try:
        threshold = float(value)
    except (TypeError, ValueError):
        return DEFAULT_SPAM_THRESHOLD

    if not math.isfinite(threshold) or not 0 <= threshold <= 1:
        return DEFAULT_SPAM_THRESHOLD
    return threshold
