import logging
import os
import sys
from datetime import datetime


def _get_log_dir():
    if getattr(sys, 'frozen', False):
        base = os.path.dirname(sys.executable)
    else:
        base = os.path.dirname(os.path.abspath(__file__))
    return os.path.join(base, 'logs')


def setup_logger():
    log_dir = _get_log_dir()
    os.makedirs(log_dir, exist_ok=True)

    logger = logging.getLogger('temperature')
    logger.setLevel(logging.DEBUG)

    if logger.handlers:
        return logger

    today = datetime.now().strftime('%Y%m%d')
    log_file = os.path.join(log_dir, f'app_{today}.log')

    file_handler = logging.FileHandler(log_file, encoding='utf-8')
    file_handler.setLevel(logging.DEBUG)
    file_handler.setFormatter(logging.Formatter(
        '%(asctime)s [%(levelname)s] %(message)s',
        datefmt='%Y-%m-%d %H:%M:%S'
    ))

    logger.addHandler(file_handler)
    return logger


def get_logger():
    logger = logging.getLogger('temperature')
    if not logger.handlers:
        setup_logger()
    return logger


def sanitize_text(text):
    if text is None:
        return ''
    result = str(text)
    for ch in ['℃', '°C']:
        result = result.replace(ch, '')
    parts = result.split(',')
    sanitized = []
    for p in parts:
        p = p.strip()
        try:
            float(p)
            sanitized.append('[数值]')
        except ValueError:
            if '/' in p and len(p) <= 20:
                sanitized.append('[时间]')
            else:
                sanitized.append('[文本]')
    return ', '.join(sanitized)
