import logging
import os
import sys
from datetime import datetime

def setup_logger():
    """로깅 시스템 설정 - 파일과 콘솔 동시 출력"""
    # PyInstaller 실행 시 올바른 경로 설정
    if getattr(sys, 'frozen', False):
        application_path = os.path.dirname(sys.executable)
    else:
        application_path = os.path.dirname(os.path.abspath(__file__))

    # logs 폴더 생성
    log_dir = os.path.join(application_path, "logs")
    if not os.path.exists(log_dir):
        os.makedirs(log_dir)

    # 로그 파일명: logs/YYYY-MM-DD.log
    log_filename = os.path.join(log_dir, f"{datetime.now().strftime('%Y-%m-%d')}.log")

    # 로거 설정
    logger = logging.getLogger('NEIS_Auto')
    logger.setLevel(logging.INFO)

    # 기존 핸들러 제거 (중복 방지)
    if logger.handlers:
        logger.handlers.clear()

    # 파일 핸들러 (UTF-8 인코딩)
    file_handler = logging.FileHandler(log_filename, encoding='utf-8')
    file_handler.setLevel(logging.INFO)

    # 콘솔 핸들러
    console_handler = logging.StreamHandler()
    console_handler.setLevel(logging.INFO)

    # 포맷 설정
    formatter = logging.Formatter('[%(asctime)s] [%(levelname)s] %(message)s', datefmt='%H:%M:%S')
    file_handler.setFormatter(formatter)
    console_handler.setFormatter(formatter)

    # 핸들러 추가
    logger.addHandler(file_handler)
    logger.addHandler(console_handler)

    return logger

# 전역 로거 인스턴스
logger = setup_logger()
