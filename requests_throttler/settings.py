
###----------------------###
#---- Logging settings ----#
###----------------------###

# Removed logging settings as this will be handled by the root logger
# 
# Logging is provided throughout the request throttling process and is sent to the root logger in the application that calls this library.
# Instantiate a logger object using logger = logging.getLogger() - note that no argument is provided for a root logger.
# This will act as the parent logger for this library's own logger and will control all logging output/formatting
# The root logger will need to be configured with file and/or stream handlers as per: https://docs.python.org/3/howto/logging.html#logging-advanced-tutorial