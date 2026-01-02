import logging 
import os
import ksubscribe_share.config as Config
from logging.handlers import TimedRotatingFileHandler
from datetime import datetime
import pytz
import time

class KSTFormatter(logging.Formatter):
    """한국 시간대(KST)를 사용하는 로그 포맷터"""
    def __init__(self, fmt=None, datefmt=None):
        super().__init__(fmt, datefmt)
        self.kst = pytz.timezone('Asia/Seoul')
    
    def formatTime(self, record, datefmt=None):
        """로그 레코드의 시간을 KST로 변환하여 포맷팅"""
        ct = datetime.fromtimestamp(record.created, tz=self.kst)
        if datefmt:
            s = ct.strftime(datefmt)
        else:
            t = ct.strftime("%Y-%m-%d %H:%M:%S")
            s = "%s,%03d" % (t, record.msecs)
        return s


class Logger():
    
    _instance = None
    log_dir = Config.LOG_DIR
    docker_collect_logger_name = "docker_collect"
    docker_scraping_logger_name = "docker_scraping"
    docker_scraping_result_logger_name = "docker_scraping_result" # total cnt, delete cnt 등 summary만 logging
    docker_daily_history_logger_name = "docker_daily_history"
    docker_talk_send_logger_name = "docker_talk_send"
    ksubscribe_server_logger_name = "ksubscribe_server"
    
    def __new__(cls, *args, **kwargs):
        if not cls._instance:
            cls._instance = super(Logger, cls).__new__(cls, *args, **kwargs)
        return cls._instance

    def __init__(self):
        
        
        pass

    # # # 모듈화된 로깅 설정
    # def setup_logger(self, name: str) -> logging.Logger:
    #     """
    #     name에 따라 로그 파일을 다르게 생성하고, 특정 위치(log_dir)에 저장
    #     """
    #     # 로그 디렉토리 생성
    #     if not os.path.exists(self.log_dir):
    #         os.makedirs(self.log_dir)

    #     # 파일 경로 설정
    #     log_file = os.path.join(self.log_dir, f"{name}.log")

    #     logger = logging.getLogger(name)
    #     if not logger.handlers:  # 중복 설정 방지
            
    #         # 파일 핸들러 설정
    #         file_handler = logging.FileHandler(log_file, mode="a")
    #         file_formatter = logging.Formatter("%(asctime)s - %(name)s - %(levelname)s - %(message)s")
    #         file_handler.setFormatter(file_formatter)
    #         logger.addHandler(file_handler)
            
    #         # 콘솔 핸들러 설정
    #         console_handler = logging.StreamHandler()
    #         console_formatter = logging.Formatter("%(asctime)s - %(name)s - %(levelname)s - %(message)s")
    #         console_handler.setFormatter(console_formatter)
    #         logger.addHandler(console_handler)
            
    #         logger.setLevel(logging.INFO)
            
    #     return logger


    def setup_logger(self, name: str) -> logging.Logger:
            """
            name에 따라 로그 파일을 날짜별로 다르게 생성하고, 특정 위치(log_dir)에 저장
            """
            # 로그 디렉토리 생성
            if not os.path.exists(self.log_dir):
                os.makedirs(self.log_dir)

            # 파일 경로 설정 (파일 이름은 name)
            log_file = os.path.join(self.log_dir, f"{name}.log")

            logger = logging.getLogger(name)
            if not logger.handlers:  # 중복 설정 방지

                # 날짜별 로그 파일 핸들러 설정
                file_handler = TimedRotatingFileHandler(
                    log_file, when="midnight", interval=1, backupCount=7, encoding="utf-8"
                )                
                file_handler.suffix = "%Y-%m-%d"  # 로그 파일에 날짜 추가


                file_formatter = KSTFormatter("%(asctime)s - %(name)s - %(levelname)s - %(message)s")
                file_handler.setFormatter(file_formatter)
                logger.addHandler(file_handler)

                # 콘솔 핸들러 설정
                console_handler = logging.StreamHandler()
                console_formatter = KSTFormatter("%(asctime)s - %(name)s - %(levelname)s - %(message)s")
                console_handler.setFormatter(console_formatter)
                logger.addHandler(console_handler)

                # 로그 레벨 설정
                logger.setLevel(logging.INFO)

                # 파일 핸들러에 날짜별로 새 파일 생성 옵션 추가

            return logger
    
