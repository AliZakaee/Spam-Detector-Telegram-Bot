import unittest

from preprocessing import _fallback_normalize, normalize_text


class FallbackNormalizationTests(unittest.TestCase):
    def test_unifies_arabic_letters_and_digits(self):
        self.assertEqual(_fallback_normalize("يكى ١٢۳"), "یکی 123")

    def test_removes_formatting_marks_and_collapses_whitespace(self):
        text = "سَـلام‌‏\t  دنیا"

        self.assertEqual(_fallback_normalize(text), "سلام دنیا")


class NormalizeTextContractTests(unittest.TestCase):
    def test_non_string_and_blank_values_return_empty_text(self):
        for value in (None, "", 0, False, [], {}):
            with self.subTest(value=value):
                self.assertEqual(normalize_text(value), "")

    def test_plain_persian_text_is_preserved(self):
        self.assertEqual(normalize_text("سلام"), "سلام")


if __name__ == "__main__":
    unittest.main()
