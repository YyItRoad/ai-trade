import logging
import sys
from pathlib import Path
import colorlog

def setup_logging():
    """
    配置全局日志记录器，将日志同时输出到控制台和文件。
    """
    LOGS_DIR = Path("logs")
    LOGS_DIR.mkdir(exist_ok=True)
    APP_LOG_FILE = LOGS_DIR / "app.log"

    # 获取根记录器
    root_logger = logging.getLogger()
    # 只有在没有配置 handlers 的情况下才进行配置，防止重复
    if not root_logger.handlers:
        root_logger.setLevel(logging.INFO)

        # 1. 控制台 Handler (带颜色)
        color_formatter = colorlog.ColoredFormatter(
            '%(log_color)s%(asctime)s - %(name)s - %(levelname)s - %(message)s',
            datefmt="%Y-%m-%d %H:%M:%S",
            log_colors={
                'DEBUG':    'cyan',
                'INFO':     'green',
                'WARNING':  'yellow',
                'ERROR':    'red',
                'CRITICAL': 'red,bg_white',
            }
        )
        stream_handler = colorlog.StreamHandler(sys.stdout)
        stream_handler.setFormatter(color_formatter)
        root_logger.addHandler(stream_handler)

        # 2. 文件 Handler (不带颜色)
        file_formatter = logging.Formatter(
            "%(asctime)s - %(name)s - %(levelname)s - %(message)s",
            datefmt="%Y-%m-%d %H:%M:%S"
        )
        file_handler = logging.FileHandler(APP_LOG_FILE, mode='a', encoding='utf-8')
        file_handler.setFormatter(file_formatter)
        root_logger.addHandler(file_handler)

        logging.info("全局日志记录器已成功配置 (控制台带颜色)。")

    # 将 uvicorn 的日志也交由根记录器处理，以统一格式和输出
    logging.getLogger("uvicorn").handlers = root_logger.handlers
    logging.getLogger("uvicorn.access").handlers = root_logger.handlers
    logging.getLogger("uvicorn.error").handlers = root_logger.handlers
