import csv
import os
from datetime import datetime
from dataclasses import dataclass

from src.logger import get_logger, sanitize_text


@dataclass
class TemperatureRecord:
    timestamp: datetime
    temperature: float


def parse_temperature(raw_value):
    cleaned = raw_value.replace('℃', '').replace('°C', '').strip()
    return float(cleaned)


def parse_timestamp(raw_value):
    raw_value = raw_value.strip()
    for fmt in ['%Y/%m/%d %H:%M', '%Y-%m-%d %H:%M:%S', '%Y-%m-%d %H:%M',
                '%Y/%m/%d %H:%M:%S', '%Y/%m/%d %H:%M:%S']:
        try:
            return datetime.strptime(raw_value, fmt)
        except ValueError:
            continue
    raise ValueError(f"无法解析时间格式: {sanitize_text(raw_value)}")


def read_single_csv(filepath):
    logger = get_logger()
    filename = os.path.basename(filepath)
    records = []

    encodings = ['gbk', 'gb18030', 'utf-8-sig', 'utf-8']
    f = None
    used_encoding = None
    for enc in encodings:
        try:
            f = open(filepath, 'r', encoding=enc)
            f.read(1024)
            f.seek(0)
            used_encoding = enc
            break
        except (UnicodeDecodeError, LookupError):
            if f:
                f.close()
            f = None
            continue

    if f is None:
        logger.error(f"无法解码文件: {filename}")
        raise ValueError(f"无法解码文件: {filename}")

    try:
        reader = csv.reader(f)
        header = next(reader, None)
        if header is None:
            logger.error(f"文件为空: {filename}")
            raise ValueError(f"文件为空: {filename}")

        header = [h.strip() for h in header]
        col_map = _detect_columns(header)

        row_count = 0
        error_count = 0
        for row in reader:
            if len(row) < 6:
                error_count += 1
                continue
            try:
                ts = parse_timestamp(row[col_map['time']])
                temp = parse_temperature(row[col_map['data']])
                records.append(TemperatureRecord(ts, temp))
                row_count += 1
            except (ValueError, IndexError) as e:
                error_count += 1
                logger.debug(f"文件 {filename} 第 {row_count + error_count} 行解析失败: {e}")

        logger.info(f"文件 {filename} 加载完成: 有效 {row_count} 行, 错误 {error_count} 行, 编码 {used_encoding}")
    finally:
        f.close()

    return records


def _detect_columns(header):
    col_map = {}
    for i, col in enumerate(header):
        if col == '数据':
            col_map['data'] = i
        elif col == '时间':
            col_map['time'] = i
        elif col == '设备名称':
            col_map['device'] = i
        elif col == '部门':
            col_map['dept'] = i

    if 'data' not in col_map:
        raise ValueError(f"无法找到数据列, 表头为: {sanitize_text(','.join(header))}")
    if 'time' not in col_map:
        raise ValueError(f"无法找到时间列, 表头为: {sanitize_text(','.join(header))}")

    return col_map


def read_csv_files(filepaths):
    logger = get_logger()
    all_records = []
    seen_timestamps = set()

    for filepath in filepaths:
        try:
            records = read_single_csv(filepath)
            for r in records:
                key = r.timestamp
                if key not in seen_timestamps:
                    all_records.append(r)
                    seen_timestamps.add(key)
        except (ValueError, OSError) as e:
            logger.error(f"读取文件失败: {os.path.basename(filepath)}, 错误: {e}")

    all_records.sort(key=lambda r: r.timestamp)

    total = len(all_records)
    if total > 0:
        logger.info(f"全部文件加载完成: 共 {total} 条记录, 时间范围 "
                    f"{all_records[0].timestamp.strftime('%Y-%m-%d %H:%M')} ~ "
                    f"{all_records[-1].timestamp.strftime('%Y-%m-%d %H:%M')}")
    else:
        logger.warning("未加载到任何有效记录")

    return all_records


def filter_by_range(records, start_time, end_time):
    return [r for r in records if start_time <= r.timestamp <= end_time]
