import logging
from logging.handlers import TimedRotatingFileHandler
from pathlib import Path

logfile = Path(__file__).resolve().parents[1] / 'log' / 'blog.log'
logfile.parent.mkdir(parents=True, exist_ok=True)

logger = logging.getLogger(__name__)
logger.setLevel(logging.INFO)

if not logger.handlers:
    handler = TimedRotatingFileHandler(str(logfile), when='midnight', interval=1)
    handler.setFormatter(logging.Formatter('%(asctime)s %(levelname)s %(threadName)-10s %(message)s'))
    handler.suffix = '%Y%m%d'
    logger.addHandler(handler)
