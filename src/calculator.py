from dataclasses import dataclass
from datetime import datetime, timedelta
from enum import Enum
from typing import List

from src.csv_reader import TemperatureRecord
from src.logger import get_logger
from src.mkt import calculate_mkt


class AlertType(Enum):
    NORMAL = "温度正常"
    HIGH = "高温报警"
    LOW = "低温报警"


@dataclass
class AlertSegment:
    start: datetime
    end: datetime
    alert_type: AlertType
    duration_minutes: int


@dataclass
class SummaryRow:
    status: str
    duration: str
    duration_minutes: int
    percentage: float
    alert_count: int


@dataclass
class StatisticsInfo:
    start_time: datetime
    end_time: datetime
    total_duration: str
    total_minutes: int
    temp_max: float
    temp_min: float
    temp_avg: float
    mkt: float
    data_count: int


@dataclass
class CalculationResult:
    segments: List[AlertSegment]
    summary: List[SummaryRow]
    statistics: StatisticsInfo


def classify_temperature(temp, high_threshold, low_threshold):
    if temp > high_threshold:
        return AlertType.HIGH
    if temp < low_threshold:
        return AlertType.LOW
    return AlertType.NORMAL


def build_segments(records, high_threshold, low_threshold):
    if not records:
        return []

    segments = []
    current_type = classify_temperature(
        records[0].temperature, high_threshold, low_threshold
    )
    current_start = records[0].timestamp

    for i in range(1, len(records)):
        record_type = classify_temperature(
            records[i].temperature, high_threshold, low_threshold
        )
        if record_type != current_type:
            current_end = records[i - 1].timestamp
            duration = int((current_end - current_start).total_seconds() / 60)
            segments.append(AlertSegment(
                current_start, current_end, current_type, duration
            ))
            current_type = record_type
            current_start = records[i].timestamp

    current_end = records[-1].timestamp
    duration = int((current_end - current_start).total_seconds() / 60)
    segments.append(AlertSegment(
        current_start, current_end, current_type, duration
    ))

    return segments


def format_duration(minutes):
    if minutes <= 0:
        return "0分钟"
    days = minutes // (24 * 60)
    hours = (minutes % (24 * 60)) // 60
    mins = minutes % 60
    parts = []
    if days > 0:
        parts.append(f"{days}天")
    if hours > 0:
        parts.append(f"{hours}小时")
    if mins > 0:
        parts.append(f"{mins}分钟")
    return ''.join(parts)


def build_summary(segments, total_minutes):
    type_groups = {AlertType.NORMAL: [], AlertType.HIGH: [], AlertType.LOW: []}
    for seg in segments:
        type_groups[seg.alert_type].append(seg)

    rows = []
    order = [
        (AlertType.NORMAL, 1, "—"),
        (AlertType.HIGH, 2, len(type_groups[AlertType.HIGH])),
        (AlertType.LOW, 3, len(type_groups[AlertType.LOW])),
    ]

    for alert_type, seq, count in order:
        segs = type_groups[alert_type]
        duration_mins = sum(s.duration_minutes for s in segs)
        pct = (duration_mins / total_minutes * 100) if total_minutes > 0 else 0.0
        rows.append(SummaryRow(
            status=alert_type.value,
            duration=format_duration(duration_mins),
            duration_minutes=duration_mins,
            percentage=round(pct, 1),
            alert_count=count,
        ))

    return rows


def build_statistics(records, segments, activation_energy):
    if not records:
        return StatisticsInfo(
            start_time=datetime.min, end_time=datetime.min,
            total_duration="0分钟", total_minutes=0,
            temp_max=0, temp_min=0, temp_avg=0,
            mkt=0, data_count=0
        )

    start_time = records[0].timestamp
    end_time = records[-1].timestamp
    total_minutes = int((end_time - start_time).total_seconds() / 60)

    temps = [r.temperature for r in records]
    temp_max = max(temps)
    temp_min = min(temps)
    temp_avg = round(sum(temps) / len(temps), 2)
    mkt = calculate_mkt(temps, activation_energy)

    return StatisticsInfo(
        start_time=start_time,
        end_time=end_time,
        total_duration=format_duration(total_minutes),
        total_minutes=total_minutes,
        temp_max=temp_max,
        temp_min=temp_min,
        temp_avg=temp_avg,
        mkt=round(mkt, 2),
        data_count=len(records),
    )


def calculate(records, high_threshold, low_threshold, activation_energy=83.144):
    logger = get_logger()

    if not records:
        logger.warning("计算区间内无数据记录")
        return CalculationResult(
            segments=[],
            summary=[],
            statistics=StatisticsInfo(
                start_time=datetime.min, end_time=datetime.min,
                total_duration="0分钟", total_minutes=0,
                temp_max=0, temp_min=0, temp_avg=0,
                mkt=0, data_count=0
            )
        )

    segments = build_segments(records, high_threshold, low_threshold)
    total_minutes = segments[0].duration_minutes + sum(
        s.duration_minutes for s in segments[1:]
    ) if segments else 0

    summary = build_summary(segments, total_minutes)
    statistics = build_statistics(records, segments, activation_energy)

    high_count = sum(1 for s in segments if s.alert_type == AlertType.HIGH)
    low_count = sum(1 for s in segments if s.alert_type == AlertType.LOW)
    logger.info(f"计算完成: 数据 {statistics.data_count} 条, "
                f"高温报警 {high_count} 次, 低温报警 {low_count} 次, "
                f"总时长 {statistics.total_duration}")

    return CalculationResult(segments=segments, summary=summary, statistics=statistics)
