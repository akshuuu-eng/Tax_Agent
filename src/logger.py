import logging
import os
from datetime import datetime

# Creates logs directory
LOG_DIR = os.path.join(os.path.dirname(os.path.dirname(os.path.abspath(__file__))), "data", "logs")
os.makedirs(LOG_DIR, exist_ok=True)

def setup_logger(name=__name__):
    logger = logging.getLogger(name)
    if logger.hasHandlers():
        return logger
        
    logger.setLevel(logging.INFO)
    
    # File Handler
    log_filename = f"ita_{datetime.now().strftime('%Y%m%d')}.log"
    file_handler = logging.FileHandler(os.path.join(LOG_DIR, log_filename))
    file_fmt = logging.Formatter('%(asctime)s - %(name)s - %(levelname)s - %(message)s')
    file_handler.setFormatter(file_fmt)
    
    # Console Handler
    console_handler = logging.StreamHandler()
    console_fmt = logging.Formatter('%(levelname)s: %(message)s')
    console_handler.setFormatter(console_fmt)
    
    logger.addHandler(file_handler)
    logger.addHandler(console_handler)
    
    return logger

# Global logger instance for simple usage
logger = setup_logger("ITA_Core")
