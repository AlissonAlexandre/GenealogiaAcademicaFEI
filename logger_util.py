from datetime import datetime
import pytz
import logging

_logger = None

def get_logger():
    global _logger
    if _logger is not None:
        return _logger 

    # Configuração do logger
    logger = logging.getLogger("global_logger")
    logger.setLevel(logging.DEBUG)

    tz_sp = pytz.timezone("America/Sao_Paulo")
    log_formatter = logging.Formatter('%(asctime)s - %(levelname)s - %(message)s')

    log_filename = 'log-' + datetime.now(tz_sp).strftime('%Y-%m-%d_%H-%M-%S') + '.log'
    file_handler = logging.FileHandler(log_filename, encoding='utf-8')
    file_handler.setFormatter(log_formatter)
    file_handler.setLevel(logging.DEBUG)

    console_handler = logging.StreamHandler()
    console_handler.setFormatter(log_formatter)
    console_handler.setLevel(logging.DEBUG)
    
    logger.addHandler(file_handler)
    logger.addHandler(console_handler)

    _logger = logger  
    return logger