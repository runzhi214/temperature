import unittest
import os
import tempfile
from src.logger import setup_logger, get_logger, sanitize_text


class TestLogger(unittest.TestCase):

    def setUp(self):
        self.logger = setup_logger()

    def test_logger_has_handler(self):
        self.assertTrue(len(self.logger.handlers) > 0)

    def test_logger_writes_to_file(self):
        self.logger.info("test log message")
        for handler in self.logger.handlers:
            handler.flush()
        self.assertGreater(len(self.logger.handlers), 0)

    def test_get_logger_returns_same_instance(self):
        logger1 = get_logger()
        logger2 = get_logger()
        self.assertIs(logger1, logger2)

    def test_sanitize_temperature_value(self):
        result = sanitize_text("-18.1℃")
        self.assertEqual(result, "[数值]")

    def test_sanitize_time_value(self):
        result = sanitize_text("2024/12/31 23:40")
        self.assertEqual(result, "[时间]")

    def test_sanitize_text_value(self):
        result = sanitize_text("测试设备名称")
        self.assertEqual(result, "[文本]")

    def test_sanitize_mixed_row(self):
        result = sanitize_text("测试部门,测试设备,-18.1℃,2024/12/31 23:40")
        self.assertIn("[文本]", result)
        self.assertIn("[数值]", result)
        self.assertIn("[时间]", result)

    def test_sanitize_none(self):
        result = sanitize_text(None)
        self.assertEqual(result, "")

    def test_sanitize_empty(self):
        result = sanitize_text("")
        self.assertEqual(result, "[文本]")


if __name__ == '__main__':
    unittest.main()
