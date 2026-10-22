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
        if len(header) == 1:
            return _read_compact_records(reader, filename, used_encoding)
        return _read_table_records(reader, filename, header, used_encoding)
    finally:
        f.close()


def _read_table_records(reader, filename, header, used_encoding):
    logger = get_logger()
    col_map = _detect_columns(header)

    records = []
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
    return records


# 单列紧凑格式(CTE 导出): 每行整体带双引号, 内部以制表符分隔 序号/时间/温度 三列,
# 温度后带尾随制表符; csv.reader 将整行读为单字段, 故按制表符拆分。
# 如 "10\t5/28/2020 17:16:00\t-15.0625\t" 表示序号10, 2020-05-28 17:16:00, 温度-15.0625;
# 温度负号自带, 正温度无符号, 最多 4 位小数
_COMPACT_TS_FORMAT = '%m/%d/%Y %H:%M:%S'


def _read_compact_records(reader, filename, used_encoding):
    logger = get_logger()

    records = []
    row_count = 0
    error_count = 0
    for row in reader:
        record = None
        if len(row) == 1:
            record = _parse_compact_row(row[0])
        if record is None:
            error_count += 1
            logger.debug(f"文件 {filename} 第 {row_count + error_count} 行解析失败: 不符合单列紧凑格式")
            continue
        records.append(record)
        row_count += 1

    if row_count == 0:
        logger.error(f"单列文件无有效数据行: {filename}")
        raise ValueError(f"单列文件无有效数据行: {filename}")

    logger.info(f"文件 {filename} 加载完成: 格式 单列紧凑, 有效 {row_count} 行, 错误 {error_count} 行, 编码 {used_encoding}")
    return records


def _parse_compact_row(raw_value):
    """解析单列紧凑格式数据行, 返回记录或 None。

    行内为制表符分隔的 序号/时间/温度 三列, 尾随制表符产生空尾段。
    部分行仅有日期无时刻(实测 137 行, 均夹在前一日 23:50 与当日
    00:10 之间, 为采集器日界行的导出缺陷), 按当日 00:00:00 恢复;
    字段数不符或时间/温度解析失败的行返回 None, 由调用方按错误行跳过。
    """
    parts = [p.strip() for p in raw_value.split('\t')]
    if parts and parts[-1] == '':
        parts = parts[:-1]
    if len(parts) != 3:
        return None

    ts = None
    for fmt in (_COMPACT_TS_FORMAT, '%m/%d/%Y'):
        try:
            ts = datetime.strptime(parts[1], fmt)
            break
        except ValueError:
            continue
    if ts is None:
        return None

    try:
        temp = parse_temperature(parts[2])
    except ValueError:
        return None
    return TemperatureRecord(ts, temp)


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
