import unittest

from core.config import DEFAULT_SPAM_THRESHOLD, parse_spam_threshold


class ParseSpamThresholdTests(unittest.TestCase):
    def test_accepts_probability_boundaries_and_values(self):
        for value, expected in (("0", 0.0), ("0.75", 0.75), ("1", 1.0)):
            with self.subTest(value=value):
                self.assertEqual(parse_spam_threshold(value), expected)

    def test_invalid_values_use_safe_default(self):
        for value in (None, "", "invalid", "-0.1", "1.1", "nan", "inf", "-inf"):
            with self.subTest(value=value):
                self.assertEqual(parse_spam_threshold(value), DEFAULT_SPAM_THRESHOLD)


if __name__ == "__main__":
    unittest.main()
