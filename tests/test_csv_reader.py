import unittest
import os
import tempfile
from datetime import datetime

from src.csv_reader import (
    parse_temperature, parse_timestamp, read_single_csv,
    read_csv_files, filter_by_range, TemperatureRecord
)


class TestParseTemperature(unittest.TestCase):

    def test_parse_simple_negative(self):
        self.assertEqual(parse_temperature("-18.1℃"), -18.1)

    def test_parse_positive(self):
        self.assertEqual(parse_temperature("25.3℃"), 25.3)

    def test_parse_alt_unit(self):
        self.assertEqual(parse_temperature("30.0°C"), 30.0)

    def test_parse_no_unit(self):
        self.assertEqual(parse_temperature("-18.1"), -18.1)

    def test_parse_integer(self):
        self.assertEqual(parse_temperature("-18℃"), -18.0)


class TestParseTimestamp(unittest.TestCase):

    def test_slash_format(self):
        result = parse_timestamp("2024/12/31 23:40")
        self.assertEqual(result, datetime(2024, 12, 31, 23, 40))

    def test_dash_format(self):
        result = parse_timestamp("2024-12-31 23:40:00")
        self.assertEqual(result, datetime(2024, 12, 31, 23, 40, 0))

    def test_dash_no_seconds(self):
        result = parse_timestamp("2024-12-31 23:40")
        self.assertEqual(result, datetime(2024, 12, 31, 23, 40))

    def test_invalid_raises(self):
        with self.assertRaises(ValueError):
            parse_timestamp("not-a-date")


class TestReadSingleCsv(unittest.TestCase):

    def _create_csv(self, content, encoding='gbk'):
        fd, path = tempfile.mkstemp(suffix='.csv')
        with os.fdopen(fd, 'w', encoding=encoding) as f:
            f.write(content)
        return path

    def test_read_normal_file(self):
        content = "部门,设备名称,采集器编码,传感器名称,数据,时间\n"
        content += "测试部,设备A,CODE1,温度,-18.1℃,2024/12/31 23:40\n"
        content += "测试部,设备A,CODE1,温度,-18.3℃,2024/12/31 23:20\n"
        path = self._create_csv(content)
        try:
            records = read_single_csv(path)
            self.assertEqual(len(records), 2)
            self.assertEqual(records[0].temperature, -18.1)
            self.assertEqual(records[0].timestamp, datetime(2024, 12, 31, 23, 40))
        finally:
            os.unlink(path)

    def test_read_utf8_file(self):
        content = "部门,设备名称,采集器编码,传感器名称,数据,时间\n"
        content += "测试部,设备A,CODE1,温度,25.0℃,2024/12/31 23:40\n"
        path = self._create_csv(content, encoding='utf-8-sig')
        try:
            records = read_single_csv(path)
            self.assertEqual(len(records), 1)
            self.assertEqual(records[0].temperature, 25.0)
        finally:
            os.unlink(path)

    def test_read_skips_bad_rows(self):
        content = "部门,设备名称,采集器编码,传感器名称,数据,时间\n"
        content += "测试部,设备A,CODE1,温度,-18.1℃,2024/12/31 23:40\n"
        content += "测试部,设备A,CODE1,温度,无效,2024/12/31 23:20\n"
        content += "短行\n"
        path = self._create_csv(content)
        try:
            records = read_single_csv(path)
            self.assertEqual(len(records), 1)
        finally:
            os.unlink(path)

    def test_read_empty_file_raises(self):
        path = self._create_csv("")
        try:
            with self.assertRaises(ValueError):
                read_single_csv(path)
        finally:
            os.unlink(path)


class TestReadCsvFiles(unittest.TestCase):

    def _create_csv(self, content, encoding='gbk'):
        fd, path = tempfile.mkstemp(suffix='.csv')
        with os.fdopen(fd, 'w', encoding=encoding) as f:
            f.write(content)
        return path

    def test_merge_and_sort(self):
        content1 = "部门,设备名称,采集器编码,传感器名称,数据,时间\n"
        content1 += "测试部,设备A,CODE1,温度,-18.1℃,2024/12/31 23:40\n"
        content2 = "部门,设备名称,采集器编码,传感器名称,数据,时间\n"
        content2 += "测试部,设备A,CODE1,温度,-18.3℃,2024/12/31 23:20\n"
        path1 = self._create_csv(content1)
        path2 = self._create_csv(content2)
        try:
            records = read_csv_files([path1, path2])
            self.assertEqual(len(records), 2)
            self.assertTrue(records[0].timestamp < records[1].timestamp)
        finally:
            os.unlink(path1)
            os.unlink(path2)

    def test_deduplicate(self):
        content = "部门,设备名称,采集器编码,传感器名称,数据,时间\n"
        content += "测试部,设备A,CODE1,温度,-18.1℃,2024/12/31 23:40\n"
        path1 = self._create_csv(content)
        path2 = self._create_csv(content)
        try:
            records = read_csv_files([path1, path2])
            self.assertEqual(len(records), 1)
        finally:
            os.unlink(path1)
            os.unlink(path2)


class TestFilterByRange(unittest.TestCase):

    def test_filter(self):
        records = [
            TemperatureRecord(datetime(2024, 10, 1, 10, 0), 20.0),
            TemperatureRecord(datetime(2024, 10, 2, 10, 0), 25.0),
            TemperatureRecord(datetime(2024, 10, 3, 10, 0), 30.0),
        ]
        result = filter_by_range(
            records,
            datetime(2024, 10, 2, 0, 0),
            datetime(2024, 10, 3, 0, 0)
        )
        self.assertEqual(len(result), 1)
        self.assertEqual(result[0].temperature, 25.0)


if __name__ == '__main__':
    unittest.main()
