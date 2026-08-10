import io
import logging
import os
import tempfile
import unittest

from core.logging_config import configure_error_file_logging


class ErrorFileLoggingTests(unittest.TestCase):
    def test_errors_reach_file_without_noisy_console_output(self):
        logger = logging.Logger("test-bot-logger")
        console_output = io.StringIO()
        console_handler = logging.StreamHandler(console_output)
        logger.addHandler(console_handler)

        with tempfile.TemporaryDirectory() as directory:
            log_path = os.path.join(directory, "bot.log")
            file_handler = configure_error_file_logging(logger, log_path)
            self.addCleanup(file_handler.close)

            logger.error("callback failed")
            file_handler.flush()

            with open(log_path, encoding="utf-8") as log_file:
                self.assertIn("ERROR - callback failed", log_file.read())
            self.assertEqual(console_output.getvalue(), "")
            self.assertFalse(logger.propagate)


if __name__ == "__main__":
    unittest.main()
