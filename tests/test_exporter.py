import unittest
import os
import tempfile
from datetime import datetime

from openpyxl import load_workbook

from src.calculator import (
    AlertType, AlertSegment, CalculationResult,
    SummaryRow, StatisticsInfo
)
from src.exporter import export_to_excel


def make_result():
    segments = [
        AlertSegment(
            start=datetime(2024, 10, 1, 10, 0),
            end=datetime(2024, 10, 1, 10, 40),
            alert_type=AlertType.NORMAL,
            duration_seconds=2400
        ),
        AlertSegment(
            start=datetime(2024, 10, 1, 10, 40),
            end=datetime(2024, 10, 1, 10, 52),
            alert_type=AlertType.HIGH,
            duration_seconds=720
        ),
        AlertSegment(
            start=datetime(2024, 10, 1, 10, 52),
            end=datetime(2024, 10, 1, 11, 0),
            alert_type=AlertType.NORMAL,
            duration_seconds=480
        ),
    ]
    summary = [
        SummaryRow("温度正常", "48分钟", 2880, 80.0, "—"),
        SummaryRow("高温报警", "12分钟", 720, 20.0, 1),
        SummaryRow("低温报警", "0秒", 0, 0.0, 0),
    ]
    stats = StatisticsInfo(
        start_time=datetime(2024, 10, 1, 10, 0),
        end_time=datetime(2024, 10, 1, 11, 0),
        total_duration="1小时",
        total_seconds=3600,
        temp_max=35.0,
        temp_min=20.0,
        temp_avg=25.0,
        mkt=26.5,
        data_count=4
    )
    return CalculationResult(segments=segments, summary=summary, statistics=stats)


class TestExportToExcel(unittest.TestCase):

    def setUp(self):
        self.result = make_result()

    def _get_temp_path(self):
        fd, path = tempfile.mkstemp(suffix='.xlsx')
        os.close(fd)
        return path

    def test_export_creates_file(self):
        path = self._get_temp_path()
        try:
            export_to_excel([self.result], path)
            self.assertTrue(os.path.exists(path))
        finally:
            if os.path.exists(path):
                os.unlink(path)

    def test_export_multiple_sheets(self):
        path = self._get_temp_path()
        try:
            export_to_excel([self.result, self.result], path,
                            range_labels=["区间A", "区间B"])
            wb = load_workbook(path)
            self.assertEqual(len(wb.sheetnames), 2)
            self.assertIn("区间A", wb.sheetnames)
            self.assertIn("区间B", wb.sheetnames)
        finally:
            if os.path.exists(path):
                os.unlink(path)

    def test_sheet_content_summary(self):
        path = self._get_temp_path()
        try:
            export_to_excel([self.result], path)
            wb = load_workbook(path)
            ws = wb[wb.sheetnames[0]]
            title = ws.cell(row=1, column=1).value
            self.assertIn("温度监控数据分析报告", title)
        finally:
            if os.path.exists(path):
                os.unlink(path)

    def test_sheet_has_summary_headers(self):
        path = self._get_temp_path()
        try:
            export_to_excel([self.result], path)
            wb = load_workbook(path)
            ws = wb[wb.sheetnames[0]]
            found = False
            for row in ws.iter_rows(min_row=1, max_row=10, max_col=5):
                values = [c.value for c in row]
                if "序号" in values and "状态" in values and "持续时间" in values:
                    found = True
                    break
            self.assertTrue(found)
        finally:
            if os.path.exists(path):
                os.unlink(path)

    def test_sheet_has_detail_section(self):
        path = self._get_temp_path()
        try:
            export_to_excel([self.result], path)
            wb = load_workbook(path)
            ws = wb[wb.sheetnames[0]]
            found = False
            for row in ws.iter_rows(min_row=1, max_row=30, max_col=5):
                values = [c.value for c in row if c.value]
                for v in values:
                    if v == "报警明细":
                        found = True
                        break
            self.assertTrue(found)
        finally:
            if os.path.exists(path):
                os.unlink(path)

    def test_sheet_has_statistics_section(self):
        path = self._get_temp_path()
        try:
            export_to_excel([self.result], path)
            wb = load_workbook(path)
            ws = wb[wb.sheetnames[0]]
            found = False
            for row in ws.iter_rows(min_row=1, max_row=40, max_col=5):
                values = [c.value for c in row if c.value]
                for v in values:
                    if v and "MKT" in str(v):
                        found = True
                        break
            self.assertTrue(found)
        finally:
            if os.path.exists(path):
                os.unlink(path)

    def test_detail_has_alert_segments(self):
        path = self._get_temp_path()
        try:
            export_to_excel([self.result], path)
            wb = load_workbook(path)
            ws = wb[wb.sheetnames[0]]
            high_found = False
            for row in ws.iter_rows(min_row=1, max_row=30, max_col=5):
                values = [c.value for c in row]
                if "高温报警" in values:
                    high_found = True
                    break
            self.assertTrue(high_found)
        finally:
            if os.path.exists(path):
                os.unlink(path)

    def test_overview_sheet_exists(self):
        path = self._get_temp_path()
        try:
            range_times = [
                (datetime(2024, 10, 1, 10, 0), datetime(2024, 10, 1, 11, 0)),
                (datetime(2024, 10, 2, 10, 0), datetime(2024, 10, 2, 11, 0)),
            ]
            export_to_excel([self.result, self.result], path,
                            range_labels=["区间A", "区间B"],
                            range_times=range_times)
            wb = load_workbook(path)
            self.assertIn("汇总", wb.sheetnames)
        finally:
            if os.path.exists(path):
                os.unlink(path)

    def test_overview_has_correct_headers(self):
        path = self._get_temp_path()
        try:
            range_times = [(datetime(2024, 10, 1, 10, 0), datetime(2024, 10, 1, 11, 0))]
            export_to_excel([self.result], path, range_times=range_times)
            wb = load_workbook(path)
            ws = wb["汇总"]
            headers = [ws.cell(row=3, column=c).value for c in range(1, 6)]
            self.assertEqual(headers, ["序号", "开始时间", "结束时间", "状态", "持续时间"])
        finally:
            if os.path.exists(path):
                os.unlink(path)

    def test_overview_row_count_is_double_ranges(self):
        path = self._get_temp_path()
        try:
            range_times = [
                (datetime(2024, 10, 1, 10, 0), datetime(2024, 10, 1, 11, 0)),
                (datetime(2024, 10, 2, 10, 0), datetime(2024, 10, 2, 11, 0)),
                (datetime(2024, 10, 3, 10, 0), datetime(2024, 10, 3, 11, 0)),
            ]
            export_to_excel([self.result, self.result, self.result], path,
                            range_times=range_times)
            wb = load_workbook(path)
            ws = wb["汇总"]
            data_rows = 0
            for row in ws.iter_rows(min_row=4, max_col=1):
                if row[0].value is not None:
                    data_rows += 1
            self.assertEqual(data_rows, 6)
        finally:
            if os.path.exists(path):
                os.unlink(path)

    def test_overview_has_high_and_low_rows(self):
        path = self._get_temp_path()
        try:
            range_times = [(datetime(2024, 10, 1, 10, 0), datetime(2024, 10, 1, 11, 0))]
            export_to_excel([self.result], path, range_times=range_times)
            wb = load_workbook(path)
            ws = wb["汇总"]
            statuses = []
            for row in ws.iter_rows(min_row=4, max_col=4):
                if row[3].value:
                    statuses.append(row[3].value)
            self.assertIn("高温报警", statuses)
            self.assertIn("低温报警", statuses)
        finally:
            if os.path.exists(path):
                os.unlink(path)

    def test_overview_zero_duration_when_no_alert(self):
        path = self._get_temp_path()
        try:
            range_times = [(datetime(2024, 10, 1, 10, 0), datetime(2024, 10, 1, 11, 0))]
            no_alert_result = CalculationResult(
                segments=[AlertSegment(
                    start=datetime(2024, 10, 1, 10, 0),
                    end=datetime(2024, 10, 1, 11, 0),
                    alert_type=AlertType.NORMAL,
                    duration_seconds=3600
                )],
                summary=[],
                statistics=StatisticsInfo(
                    start_time=datetime(2024, 10, 1, 10, 0),
                    end_time=datetime(2024, 10, 1, 11, 0),
                    total_duration="1小时",
                    total_seconds=3600,
                    temp_max=25.0, temp_min=20.0, temp_avg=22.0,
                    mkt=22.5, data_count=3
                )
            )
            export_to_excel([no_alert_result], path, range_times=range_times)
            wb = load_workbook(path)
            ws = wb["汇总"]
            durations = []
            for row in ws.iter_rows(min_row=4, max_col=5):
                if row[4].value:
                    durations.append(row[4].value)
            self.assertEqual(len(durations), 2)
            self.assertTrue(all(d == "0秒" for d in durations))
        finally:
            if os.path.exists(path):
                os.unlink(path)


if __name__ == '__main__':
    unittest.main()
