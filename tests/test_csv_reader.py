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


class TestReadCompactCsv(unittest.TestCase):
    """单列紧凑格式: 带引号整行, 内部制表符分隔 序号/时间/温度 三列。"""

    HEADER = "Number\tDate and time\tTemperature\n"

    def _create_csv(self, content, encoding='gbk'):
        fd, path = tempfile.mkstemp(suffix='.csv')
        with os.fdopen(fd, 'w', encoding=encoding) as f:
            f.write(content)
        return path

    def _rows(self, *rows):
        return self.HEADER + ''.join(f'"{row}"\n' for row in rows)

    def test_read_compact_negative_temperature(self):
        path = self._create_csv(self._rows(
            "1\t5/28/2020 16:15:01\t-13.5625\t",
            "2\t5/28/2020 16:15:16\t-13.625\t",
        ))
        try:
            records = read_single_csv(path)
            self.assertEqual(len(records), 2)
            self.assertEqual(records[0].timestamp, datetime(2020, 5, 28, 16, 15, 1))
            self.assertEqual(records[0].temperature, -13.5625)
            self.assertEqual(records[1].timestamp, datetime(2020, 5, 28, 16, 15, 16))
            self.assertEqual(records[1].temperature, -13.625)
        finally:
            os.unlink(path)

    def test_read_compact_positive_temperature_no_sign(self):
        path = self._create_csv(self._rows(
            "4905\t7/1/2020 15:16:00\t5.0625\t",
            "4907\t7/1/2020 15:36:00\t13.8125\t",
        ))
        try:
            records = read_single_csv(path)
            self.assertEqual(len(records), 2)
            self.assertEqual(records[0].temperature, 5.0625)
            self.assertEqual(records[1].temperature, 13.8125)
        finally:
            os.unlink(path)

    def test_read_compact_integer_temperature(self):
        path = self._create_csv(self._rows("18\t5/28/2020 18:36:00\t-16\t"))
        try:
            records = read_single_csv(path)
            self.assertEqual(records[0].timestamp, datetime(2020, 5, 28, 18, 36, 0))
            self.assertEqual(records[0].temperature, -16.0)
        finally:
            os.unlink(path)

    def test_read_compact_single_digit_month_day_hour(self):
        # 月/日/小时均不补零
        path = self._create_csv(self._rows("1\t3/7/2020 8:05:00\t-20.5\t"))
        try:
            records = read_single_csv(path)
            self.assertEqual(records[0].timestamp, datetime(2020, 3, 7, 8, 5, 0))
            self.assertEqual(records[0].temperature, -20.5)
        finally:
            os.unlink(path)

    def test_read_compact_without_trailing_tab(self):
        # 尾随制表符缺失时同样可解析
        path = self._create_csv(self._rows("1\t5/28/2020 16:15:01\t-13.5625"))
        try:
            records = read_single_csv(path)
            self.assertEqual(len(records), 1)
            self.assertEqual(records[0].temperature, -13.5625)
        finally:
            os.unlink(path)

    def test_read_compact_date_only_recovers_midnight(self):
        # 仅日期无时刻的日界行按当日 00:00:00 恢复
        path = self._create_csv(self._rows(
            "41829\t3/14/2021 23:50:00\t-23.1875\t",
            "41830\t3/15/2021\t-23.5625\t",
            "41831\t3/15/2021 00:10:00\t-23.125\t",
        ))
        try:
            records = read_single_csv(path)
            self.assertEqual(len(records), 3)
            self.assertEqual(records[1].timestamp, datetime(2021, 3, 15, 0, 0, 0))
            self.assertEqual(records[1].temperature, -23.5625)
        finally:
            os.unlink(path)

    def test_read_compact_skips_bad_rows(self):
        path = self._create_csv(self._rows(
            "1\t5/28/2020 16:15:01\t-13.5625\t",
            "not-a-compact-row\t",
            "2\t32/15/2021 10:00:00\t-15\t",
            "3\t5/28/2020 16:25:00\t无效\t",
            "4\t5/28/2020 16:25:00\t-15.375\t",
        ))
        try:
            records = read_single_csv(path)
            self.assertEqual(len(records), 2)
            self.assertEqual(records[0].timestamp, datetime(2020, 5, 28, 16, 15, 1))
            self.assertEqual(records[1].timestamp, datetime(2020, 5, 28, 16, 25, 0))
            self.assertEqual(records[1].temperature, -15.375)
        finally:
            os.unlink(path)

    def test_compact_file_without_valid_rows_raises(self):
        path = self._create_csv(self._rows("not-a-compact-row\t", "another bad one\t"))
        try:
            with self.assertRaises(ValueError):
                read_single_csv(path)
        finally:
            os.unlink(path)

    def test_compact_header_only_raises(self):
        path = self._create_csv(self.HEADER)
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

    def test_mixed_formats_merge_and_sort(self):
        old_content = "部门,设备名称,采集器编码,传感器名称,数据,时间\n"
        old_content += "测试部,设备A,CODE1,温度,-18.1℃,2024/12/31 23:40\n"
        compact_content = "Number\tDate and time\tTemperature\n"
        compact_content += '"1\t5/28/2020 16:15:01\t-13.5625\t"\n'
        path_old = self._create_csv(old_content)
        path_compact = self._create_csv(compact_content)
        try:
            records = read_csv_files([path_old, path_compact])
            self.assertEqual(len(records), 2)
            self.assertEqual(records[0].timestamp, datetime(2020, 5, 28, 16, 15, 1))
            self.assertEqual(records[0].temperature, -13.5625)
            self.assertEqual(records[1].timestamp, datetime(2024, 12, 31, 23, 40))
            self.assertEqual(records[1].temperature, -18.1)
        finally:
            os.unlink(path_old)
            os.unlink(path_compact)


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

    def test_filter_with_seconds_in_data(self):
        records = [
            TemperatureRecord(datetime(2024, 10, 1, 23, 59, 30), 20.0),
            TemperatureRecord(datetime(2024, 10, 2, 0, 0, 10), 25.0),
            TemperatureRecord(datetime(2024, 10, 2, 23, 40, 9), 30.0),
        ]
        result = filter_by_range(
            records,
            datetime(2024, 10, 2, 0, 0),
            datetime(2024, 10, 2, 23, 59, 59)
        )
        self.assertEqual(len(result), 2)
        self.assertEqual(result[0].temperature, 25.0)
        self.assertEqual(result[1].temperature, 30.0)

    def test_filter_end_boundary_with_seconds(self):
        records = [
            TemperatureRecord(datetime(2024, 10, 1, 23, 59, 45), 20.0),
            TemperatureRecord(datetime(2024, 10, 2, 0, 0, 0), 25.0),
        ]
        end = datetime(2024, 10, 1, 23, 59).replace(second=59)
        result = filter_by_range(
            records,
            datetime(2024, 10, 1, 0, 0),
            end
        )
        self.assertEqual(len(result), 1)
        self.assertEqual(result[0].temperature, 20.0)


if __name__ == '__main__':
    unittest.main()
