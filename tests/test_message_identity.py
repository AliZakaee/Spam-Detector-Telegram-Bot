import unittest
from types import SimpleNamespace

from core.message_identity import get_username


class MessageIdentityTests(unittest.TestCase):
    def test_formats_user_identity(self):
        message = SimpleNamespace(
            from_user=SimpleNamespace(id=123, username="ali"),
            sender_chat=None,
        )

        self.assertEqual(get_username(message), "@ali (`123`)")

    def test_formats_channel_post_without_from_user(self):
        message = SimpleNamespace(
            from_user=None,
            sender_chat=SimpleNamespace(id=-100456, username="news"),
        )

        self.assertEqual(get_username(message), "@news (`-100456`)")

    def test_sender_chat_without_username_uses_numeric_identity(self):
        message = SimpleNamespace(
            from_user=None,
            sender_chat=SimpleNamespace(id=-100789, username=None),
        )

        self.assertEqual(
            get_username(message),
            "چت فرستنده با آیدی عددی `-100789`",
        )


if __name__ == "__main__":
    unittest.main()
