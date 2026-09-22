import sys
import os

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

from src.logger import setup_logger, get_logger
from src.gui import run


def main():
    setup_logger()
    logger = get_logger()
    logger.info("程序启动")
    try:
        run()
    except Exception as e:
        logger.error(f"程序异常退出: {e}", exc_info=True)
        raise
    logger.info("程序正常退出")


if __name__ == '__main__':
    main()
