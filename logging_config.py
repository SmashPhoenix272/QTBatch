import logging
from logging.handlers import RotatingFileHandler
import sys

def setup_logging():
    logger = logging.getLogger()
    logger.setLevel(logging.DEBUG)
    
    # Create a rotating file handler with UTF-8 encoding
    file_handler = RotatingFileHandler('qtbatch.log', maxBytes=1024*1024, backupCount=5, encoding='utf-8')
    file_handler.setLevel(logging.DEBUG)
    
    # Create a console handler with UTF-8 encoding
    console_handler = logging.StreamHandler(sys.stdout)
    console_handler.setLevel(logging.INFO)
    
    # Create a formatter
    formatter = logging.Formatter('%(asctime)s - %(name)s - %(levelname)s - %(message)s')
    file_handler.setFormatter(formatter)
    console_handler.setFormatter(formatter)
    
    # Add handlers to the logger
    logger.addHandler(file_handler)
    logger.addHandler(console_handler)
    
    return logger
