"""Shared Persian text normalization for the trainer and the bot.

Both train/train.py and core/bot.py call normalize_text() so that messages are
preprocessed identically — if they diverged, the model would see different text
at train time than at inference time and accuracy would silently drop.

hazm is used when it is installed (the richer, Persian-aware normalizer). On
environments where hazm cannot be installed (e.g. very new Python releases that
its heavy dependencies don't support yet) we fall back to an equivalent,
dependency-free character/digit normalizer. ACTIVE_BACKEND records which one is
live so both scripts can print it at startup and any mismatch is visible.
"""

import re
import unicodedata

# Arabic -> Persian letter unification and Arabic/Persian digits -> ASCII.
_CHAR_MAP = {
    "ي": "ی",  # Arabic yeh -> Persian yeh (ي -> ی)
    "ى": "ی",  # Arabic alef maksura -> Persian yeh (ى -> ی)
    "ك": "ک",  # Arabic kaf -> Persian keheh (ك -> ک)
    "ة": "ه",  # teh marbuta -> heh (ة -> ه)
    "ـ": "",        # tatweel / kashida (ـ) -> removed
    "‌": " ",       # zero-width non-joiner -> space
    "‏": "",        # right-to-left mark -> removed
    "‎": "",        # left-to-right mark -> removed
}
for _i, _base in ((0x0660, 0x0030), (0x06F0, 0x0030)):  # Arabic-Indic, Persian digits
    for _d in range(10):
        _CHAR_MAP[chr(_i + _d)] = chr(_base + _d)

_TRANSLATION = str.maketrans(_CHAR_MAP)
# Arabic harakat / diacritics (fatha, kasra, damma, sukun, superscript alef, ...).
_DIACRITICS = re.compile(r"[ً-ْٰ]")
_WHITESPACE = re.compile(r"\s+")


def _fallback_normalize(text: str) -> str:
    text = unicodedata.normalize("NFC", text)
    text = text.translate(_TRANSLATION)
    text = _DIACRITICS.sub("", text)
    return _WHITESPACE.sub(" ", text).strip()


try:
    from hazm import Normalizer as _HazmNormalizer

    _normalizer = _HazmNormalizer()
    ACTIVE_BACKEND = "hazm"

    def _normalize(text: str) -> str:
        return _normalizer.normalize(text)

except Exception:  # hazm unavailable or failed to import
    ACTIVE_BACKEND = "builtin"
    _normalize = _fallback_normalize


def normalize_text(text) -> str:
    """Return a normalized Persian string; empty string for null/blank input."""
    if not text or not isinstance(text, str):
        return ""
    return _normalize(text)
