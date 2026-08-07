import csv
import os
import tempfile
import unittest

from core.data_file import count_labeled_messages


class CountLabeledMessagesTests(unittest.TestCase):
    def write_rows(self, rows):
        temporary_file = tempfile.NamedTemporaryFile(mode="w", encoding="utf-8", newline="", delete=False)
        self.addCleanup(lambda: os.unlink(temporary_file.name))
        with temporary_file as file:
            csv.writer(file).writerows(rows)
        return temporary_file.name

    def test_header_only_file_has_no_entries(self):
        path = self.write_rows([["message", "label"]])

        self.assertEqual(count_labeled_messages(path), 0)

    def test_counts_logical_records_with_multiline_messages(self):
        path = self.write_rows([
            ["message", "label"],
            ["first line\nsecond line", "spam"],
            ["ordinary message", "normal"],
        ])

        self.assertEqual(count_labeled_messages(path), 2)

    def test_counts_legacy_headerless_records(self):
        path = self.write_rows([
            ["spam", "legacy first message"],
            ["normal", "legacy second message"],
        ])

        self.assertEqual(count_labeled_messages(path), 2)


if __name__ == "__main__":
    unittest.main()
