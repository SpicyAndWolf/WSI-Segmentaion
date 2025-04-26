import logging
from logging.handlers import TimedRotatingFileHandler
import configparser

config = configparser.ConfigParser()
config.read('config.ini')

def setup_logger():
    # 创建 logger
    logger = logging.getLogger(config['LOGCONFIG']['logger_name'])  # 统一 logger 名称
    logger.setLevel(logging.DEBUG)        # 设置全局日志级别

    # 避免重复添加处理器
    if not logger.handlers:
        # 创建文件处理器
        file_handler = TimedRotatingFileHandler(
            filename=config['LOGCONFIG']['file_name'],
            when='midnight',
            interval=1,
            backupCount=7,
            encoding='utf-8'
        )
        file_handler.setLevel(logging.DEBUG)

        # 设置日志格式
        formatter = logging.Formatter('%(asctime)s - %(name)s - %(levelname)s - %(message)s')
        file_handler.setFormatter(formatter)

        # 添加处理器到 logger
        logger.addHandler(file_handler)

    return logger