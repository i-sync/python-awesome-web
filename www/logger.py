
import logging
import os.path
from logging.handlers import TimedRotatingFileHandler

'''
Logging Levels
CRITICAL	50
ERROR	40
WARNING	30
INFO	20
DEBUG	10
NOTSET	0
'''

logfile = os.path.join(os.path.dirname(os.path.dirname(os.path.abspath(__file__))), 'log/blog.log')

#https://stackoverflow.com/questions/20240464/python-logging-file-is-not-working-when-using-logging-basicconfig
#logging.basicConfig(level=logging.INFO, format='%(asctime)s %(levelname)s %(threadName)-10s %(message)s')

logger = logging.getLogger(__name__)
logger.setLevel(logging.INFO)
handler = TimedRotatingFileHandler(logfile, when="midnight", interval=1)
handler.setFormatter(logging.Formatter('%(asctime)s %(levelname)s %(threadName)-10s %(message)s'))
handler.suffix = "%Y%m%d"
logger.addHandler(handler)
