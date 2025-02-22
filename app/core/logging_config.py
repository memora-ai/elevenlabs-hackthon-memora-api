import logging
import sys
from logging.handlers import RotatingFileHandler

def setup_logging():
    # Create a formatter
    formatter = logging.Formatter(
        '%(asctime)s - %(name)s - %(levelname)s - %(message)s'
    )

    # Create and configure the root logger
    root_logger = logging.getLogger()
    root_logger.setLevel(logging.INFO)

    # Create and configure file handler
    file_handler = RotatingFileHandler(
        'app.log',
        maxBytes=10485760,  # 10MB
        backupCount=5
    )
    file_handler.setFormatter(formatter)
    root_logger.addHandler(file_handler)

    # Create and configure console handler
    console_handler = logging.StreamHandler(sys.stdout)
    console_handler.setFormatter(formatter)
    root_logger.addHandler(console_handler)

    # Prevent logs from propagating to uvicorn's logger
    root_logger.propagate = False

    # Set logging level for specific loggers
    logging.getLogger("sqlalchemy.engine").setLevel(logging.WARNING)
    logging.getLogger("PIL").setLevel(logging.WARNING) 