import unittest

from core.config import (
    DEFAULT_CLASSIFIER_BACKEND,
    DEFAULT_CONFIDENCE_FLOOR,
    DEFAULT_SPAM_THRESHOLD,
    parse_classifier_backend,
    parse_confidence_floor,
    parse_spam_threshold,
)


class ParseSpamThresholdTests(unittest.TestCase):
    def test_accepts_probability_boundaries_and_values(self):
        for value, expected in (("0", 0.0), ("0.75", 0.75), ("1", 1.0)):
            with self.subTest(value=value):
                self.assertEqual(parse_spam_threshold(value), expected)

    def test_invalid_values_use_safe_default(self):
        for value in (None, "", "invalid", "-0.1", "1.1", "nan", "inf", "-inf"):
            with self.subTest(value=value):
                self.assertEqual(parse_spam_threshold(value), DEFAULT_SPAM_THRESHOLD)


class ParseClassifierBackendTests(unittest.TestCase):
    def test_blank_backend_uses_auto(self):
        for value in (None, "", "  "):
            with self.subTest(value=value):
                self.assertEqual(parse_classifier_backend(value), DEFAULT_CLASSIFIER_BACKEND)

    def test_backend_names_are_normalized(self):
        self.assertEqual(parse_classifier_backend("TypeSafe"), "typesafe")
        self.assertEqual(parse_classifier_backend("HYBRID"), "hybrid")
        self.assertEqual(parse_classifier_backend("svm"), "svm")

    def test_unknown_backend_raises(self):
        with self.assertRaisesRegex(ValueError, "CLASSIFIER_BACKEND"):
            parse_classifier_backend("neural")


class ParseConfidenceFloorTests(unittest.TestCase):
    def test_accepts_valid_values(self):
        self.assertEqual(parse_confidence_floor("0.75"), 0.75)

    def test_invalid_values_use_safe_default(self):
        self.assertEqual(parse_confidence_floor("nope"), DEFAULT_CONFIDENCE_FLOOR)


if __name__ == "__main__":
    unittest.main()
