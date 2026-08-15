import unittest
from types import SimpleNamespace

from core.warning_message import dismiss_warning_message


class FakeBot:
    def __init__(self, error=None):
        self.error = error
        self.deleted_messages = []

    def delete_message(self, chat_id, message_id):
        if self.error is not None:
            raise self.error
        self.deleted_messages.append((chat_id, message_id))


class DismissWarningMessageTests(unittest.TestCase):
    def test_deletes_warning_and_releases_state(self):
        bot = FakeBot()
        warning = SimpleNamespace(chat=SimpleNamespace(id=-1001), message_id=91)
        warnings = {(-1002, 42): warning}

        self.assertTrue(dismiss_warning_message(bot, warnings, -1002, 42))

        self.assertEqual(bot.deleted_messages, [(-1001, 91)])
        self.assertEqual(warnings, {})

    def test_missing_warning_is_already_resolved(self):
        bot = FakeBot()

        self.assertFalse(dismiss_warning_message(bot, {}, -1002, 42))
        self.assertEqual(bot.deleted_messages, [])

    def test_failed_delete_keeps_state_for_retry(self):
        bot = FakeBot(RuntimeError("Telegram unavailable"))
        warning = SimpleNamespace(chat=SimpleNamespace(id=-1001), message_id=91)
        warnings = {(-1002, 42): warning}

        with self.assertRaisesRegex(RuntimeError, "Telegram unavailable"):
            dismiss_warning_message(bot, warnings, -1002, 42)

        self.assertEqual(warnings, {(-1002, 42): warning})


if __name__ == "__main__":
    unittest.main()
