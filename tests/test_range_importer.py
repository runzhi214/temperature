import unittest
import os
import csv
import tempfile
from datetime import datetime

from openpyxl import Workbook

from src.range_importer import parse_flexible_time, parse_range_file


class TestParseFlexibleTime(unittest.TestCase):

    def test_slash_format(self):
        result = parse_flexible_time("2026/8/28 0:00")
        self.assertEqual(result, datetime(2026, 8, 28, 0, 0))

    def test_slash_format_with_seconds(self):
        result = parse_flexible_time("2026/8/31 23:59:30")
        self.assertEqual(result, datetime(2026, 8, 31, 23, 59, 30))

    def test_dash_format(self):
        result = parse_flexible_time("2026-09-01 00:00")
        self.assertEqual(result, datetime(2026, 9, 1, 0, 0))

    def test_dash_format_with_seconds(self):
        result = parse_flexible_time("2026-09-01 00:00:00")
        self.assertEqual(result, datetime(2026, 9, 1, 0, 0, 0))

    def test_single_digit_month_day(self):
        result = parse_flexible_time("2026/9/1 0:00")
        self.assertEqual(result, datetime(2026, 9, 1, 0, 0))

    def test_iso_format(self):
        result = parse_flexible_time("2026-09-01T00:00:00")
        self.assertEqual(result, datetime(2026, 9, 1, 0, 0, 0))

    def test_empty_string(self):
        self.assertIsNone(parse_flexible_time(""))

    def test_none(self):
        self.assertIsNone(parse_flexible_time(None))

    def test_invalid(self):
        self.assertIsNone(parse_flexible_time("invalid"))


class TestParseRangeFile(unittest.TestCase):

    def _create_xlsx(self, rows):
        fd, path = tempfile.mkstemp(suffix='.xlsx')
        os.close(fd)
        wb = Workbook()
        ws = wb.active
        for row in rows:
            ws.append(row)
        wb.save(path)
        return path

    def _create_csv(self, rows, encoding='gbk'):
        fd, path = tempfile.mkstemp(suffix='.csv')
        os.close(fd)
        with open(path, 'w', encoding=encoding) as f:
            writer = csv.writer(f)
            for row in rows:
                writer.writerow(row)
        return path

    def test_xlsx_with_header(self):
        path = self._create_xlsx([
            ['序号', '开始时间', '结束时间'],
            [1, '2026/8/28 0:00', '2026/8/31 23:59'],
            [2, '2026/9/1 0:00', '2026/9/15 23:59'],
        ])
        try:
            ranges = parse_range_file(path)
            self.assertEqual(len(ranges), 2)
            self.assertEqual(ranges[0][0], datetime(2026, 8, 28, 0, 0))
            self.assertEqual(ranges[0][1], datetime(2026, 8, 31, 23, 59))
            self.assertEqual(ranges[1][0], datetime(2026, 9, 1, 0, 0))
            self.assertEqual(ranges[1][1], datetime(2026, 9, 15, 23, 59))
        finally:
            os.unlink(path)

    def test_xlsx_without_header(self):
        path = self._create_xlsx([
            [1, '2026/8/28 0:00', '2026/8/31 23:59'],
            [2, '2026/9/1 0:00', '2026/9/15 23:59'],
        ])
        try:
            ranges = parse_range_file(path)
            self.assertEqual(len(ranges), 2)
        finally:
            os.unlink(path)

    def test_csv_with_header(self):
        path = self._create_csv([
            ['序号', '开始时间', '结束时间'],
            [1, '2026/8/28 0:00', '2026/8/31 23:59'],
            [2, '2026/9/1 0:00', '2026/9/15 23:59'],
        ])
        try:
            ranges = parse_range_file(path)
            self.assertEqual(len(ranges), 2)
        finally:
            os.unlink(path)

    def test_csv_utf8(self):
        path = self._create_csv([
            ['序号', '开始时间', '结束时间'],
            [1, '2026/8/28 0:00', '2026/8/31 23:59'],
        ], encoding='utf-8-sig')
        try:
            ranges = parse_range_file(path)
            self.assertEqual(len(ranges), 1)
        finally:
            os.unlink(path)

    def test_skips_invalid_rows(self):
        path = self._create_xlsx([
            ['序号', '开始时间', '结束时间'],
            [1, '2026/8/28 0:00', '2026/8/31 23:59'],
            [2, 'invalid', '2026/9/15 23:59'],
            [3, '2026/9/20 0:00', '2026/9/10 0:00'],
            ['short'],
        ])
        try:
            ranges = parse_range_file(path)
            self.assertEqual(len(ranges), 1)
            self.assertEqual(ranges[0][0], datetime(2026, 8, 28, 0, 0))
        finally:
            os.unlink(path)

    def test_empty_file(self):
        path = self._create_xlsx([])
        try:
            ranges = parse_range_file(path)
            self.assertEqual(len(ranges), 0)
        finally:
            os.unlink(path)

    def test_end_before_start_skipped(self):
        path = self._create_xlsx([
            ['序号', '开始时间', '结束时间'],
            [1, '2026/9/15 0:00', '2026/9/1 0:00'],
        ])
        try:
            ranges = parse_range_file(path)
            self.assertEqual(len(ranges), 0)
        finally:
            os.unlink(path)


if __name__ == '__main__':
    unittest.main()
