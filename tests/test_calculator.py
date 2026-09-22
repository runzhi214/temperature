import unittest
from datetime import datetime

from src.calculator import (
    classify_temperature, build_segments, format_duration,
    build_summary, build_statistics, calculate, AlertType
)
from src.csv_reader import TemperatureRecord


def make_records(start, temps, interval_minutes=20):
    records = []
    base = datetime(2024, 10, 1, 10, 0)
    for i, t in enumerate(temps):
        ts = datetime(
            start.year, start.month, start.day, start.hour, start.minute
        )
        from datetime import timedelta
        ts = start + timedelta(minutes=interval_minutes * i)
        records.append(TemperatureRecord(ts, t))
    return records


class TestClassifyTemperature(unittest.TestCase):

    def test_high(self):
        self.assertEqual(classify_temperature(35.0, 30.0, 10.0), AlertType.HIGH)

    def test_low(self):
        self.assertEqual(classify_temperature(5.0, 30.0, 10.0), AlertType.LOW)

    def test_normal(self):
        self.assertEqual(classify_temperature(20.0, 30.0, 10.0), AlertType.NORMAL)

    def test_equal_high_not_alert(self):
        self.assertEqual(classify_temperature(30.0, 30.0, 10.0), AlertType.NORMAL)

    def test_equal_low_not_alert(self):
        self.assertEqual(classify_temperature(10.0, 30.0, 10.0), AlertType.NORMAL)


class TestBuildSegments(unittest.TestCase):

    def test_all_normal(self):
        records = make_records(datetime(2024, 10, 1, 10, 0), [20.0, 21.0, 22.0])
        segments = build_segments(records, 30.0, 10.0)
        self.assertEqual(len(segments), 1)
        self.assertEqual(segments[0].alert_type, AlertType.NORMAL)
        self.assertEqual(segments[0].duration_minutes, 40)

    def test_high_alert_segment(self):
        records = make_records(datetime(2024, 10, 1, 10, 0), [20.0, 35.0, 35.0, 20.0])
        segments = build_segments(records, 30.0, 10.0)
        self.assertEqual(len(segments), 3)
        self.assertEqual(segments[0].alert_type, AlertType.NORMAL)
        self.assertEqual(segments[1].alert_type, AlertType.HIGH)
        self.assertEqual(segments[2].alert_type, AlertType.NORMAL)
        self.assertEqual(segments[1].duration_minutes, 20)

    def test_low_alert_segment(self):
        records = make_records(datetime(2024, 10, 1, 10, 0), [20.0, 5.0, 5.0, 20.0])
        segments = build_segments(records, 30.0, 10.0)
        self.assertEqual(len(segments), 3)
        self.assertEqual(segments[1].alert_type, AlertType.LOW)

    def test_empty_records(self):
        segments = build_segments([], 30.0, 10.0)
        self.assertEqual(len(segments), 0)

    def test_single_record(self):
        records = make_records(datetime(2024, 10, 1, 10, 0), [35.0])
        segments = build_segments(records, 30.0, 10.0)
        self.assertEqual(len(segments), 1)
        self.assertEqual(segments[0].alert_type, AlertType.HIGH)
        self.assertEqual(segments[0].duration_minutes, 0)

    def test_start_with_alert(self):
        records = make_records(datetime(2024, 10, 1, 10, 0), [35.0, 35.0, 20.0])
        segments = build_segments(records, 30.0, 10.0)
        self.assertEqual(len(segments), 2)
        self.assertEqual(segments[0].alert_type, AlertType.HIGH)
        self.assertEqual(segments[1].alert_type, AlertType.NORMAL)


class TestFormatDuration(unittest.TestCase):

    def test_zero(self):
        self.assertEqual(format_duration(0), "0分钟")

    def test_minutes_only(self):
        self.assertEqual(format_duration(45), "45分钟")

    def test_hours_and_minutes(self):
        self.assertEqual(format_duration(125), "2小时5分钟")

    def test_days_hours_minutes(self):
        self.assertEqual(format_duration(1500), "1天1小时")

    def test_days_only(self):
        self.assertEqual(format_duration(2880), "2天")


class TestBuildSummary(unittest.TestCase):

    def test_summary_structure(self):
        records = make_records(datetime(2024, 10, 1, 10, 0),
                               [20.0, 35.0, 35.0, 20.0])
        segments = build_segments(records, 30.0, 10.0)
        total = sum(s.duration_minutes for s in segments)
        summary = build_summary(segments, total)
        self.assertEqual(len(summary), 3)
        self.assertEqual(summary[0].status, "温度正常")
        self.assertEqual(summary[1].status, "高温报警")
        self.assertEqual(summary[2].status, "低温报警")
        self.assertEqual(summary[1].alert_count, 1)
        self.assertEqual(summary[2].alert_count, 0)

    def test_percentage(self):
        records = make_records(datetime(2024, 10, 1, 10, 0),
                               [20.0, 35.0, 35.0, 20.0])
        segments = build_segments(records, 30.0, 10.0)
        total = sum(s.duration_minutes for s in segments)
        summary = build_summary(segments, total)
        pct_sum = sum(r.percentage for r in summary)
        self.assertAlmostEqual(pct_sum, 100.0, places=1)

    def test_zero_total(self):
        summary = build_summary([], 0)
        self.assertEqual(len(summary), 3)
        for row in summary:
            self.assertEqual(row.percentage, 0.0)


class TestBuildStatistics(unittest.TestCase):

    def test_statistics(self):
        records = make_records(datetime(2024, 10, 1, 10, 0), [20.0, 25.0, 30.0])
        stats = build_statistics(records, [], 83.144)
        self.assertEqual(stats.temp_max, 30.0)
        self.assertEqual(stats.temp_min, 20.0)
        self.assertEqual(stats.temp_avg, 25.0)
        self.assertEqual(stats.data_count, 3)
        self.assertEqual(stats.start_time, datetime(2024, 10, 1, 10, 0))

    def test_mkt_calculated(self):
        records = make_records(datetime(2024, 10, 1, 10, 0), [25.0, 25.0])
        stats = build_statistics(records, [], 83.144)
        self.assertAlmostEqual(stats.mkt, 25.0, places=1)


class TestCalculate(unittest.TestCase):

    def test_full_calculation(self):
        records = make_records(datetime(2024, 10, 1, 10, 0),
                               [20.0, 35.0, 35.0, 5.0, 20.0])
        result = calculate(records, 30.0, 10.0)
        self.assertGreater(len(result.segments), 0)
        self.assertEqual(len(result.summary), 3)
        self.assertEqual(result.statistics.data_count, 5)
        high_count = sum(1 for s in result.segments if s.alert_type == AlertType.HIGH)
        low_count = sum(1 for s in result.segments if s.alert_type == AlertType.LOW)
        self.assertEqual(high_count, 1)
        self.assertEqual(low_count, 1)

    def test_empty_records(self):
        result = calculate([], 30.0, 10.0)
        self.assertEqual(len(result.segments), 0)
        self.assertEqual(result.statistics.data_count, 0)


if __name__ == '__main__':
    unittest.main()
