import logging

###----------------------###
#---- Logging settings ----#
###----------------------###
LOG_FORMAT_0=("[TID=%(thread)d - Thread=%(threadName)s - %(asctime)s - %(levelname)s - "
              "%(module)s.%(funcName)s(%(lineno)d)]: %(message)s")
LOG_FORMAT_1=("[Thread=%(threadName)s - %(asctime)s - %(levelname)s]: %(message)s")
LOG_FORMAT_2=("[%(asctime)s - %(levelname)s]: %(message)s")
LOG_FORMAT={logging.DEBUG: LOG_FORMAT_0,
            logging.INFO: LOG_FORMAT_1,
            logging.WARNING: LOG_FORMAT_2,
            logging.ERROR: LOG_FORMAT_0,
            logging.CRITICAL: LOG_FORMAT_0}
DEFAULT_LOG_LEVEL=logging.INFO
