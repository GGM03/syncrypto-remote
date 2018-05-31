
import logging
import sys

# logging.basicConfig(level=logging.DEBUG)
# logger = logging.getLogger(__name__)
# ch = logging.StreamHandler(sys.stdout)
# ch.setFormatter(logging.Formatter('%(name)s %(levelname)-8s %(asctime)s: "%(message)s"'))
# logger.addHandler(ch)

loggers = {}


def myLogger(name):
    global loggers
    if loggers.get(name):
        return loggers.get(name)
    else:
        logger = logging.getLogger(name)
        logger.propagate = False
        logger.setLevel(logging.DEBUG)
        # now = datetime.datetime.now()
        # handler = logging.FileHandler(
        #     '/root/credentials/Logs/ProvisioningPython'
        #     + now.strftime("%Y-%m-%d")
        #     + '.log')
        handler = logging.StreamHandler(sys.stdout)
        formatter = logging.Formatter('%(name)s: %(levelname)s %(asctime)s %(message)s')
        handler.setFormatter(formatter)
        logger.addHandler(handler)
        loggers.update(dict(name=logger))
        return logger

class Logging:
    def __init__(self, loggername):
        # self.logger = logging.getLogger(__name__)
        self.logger = myLogger(loggername)
        self._debug = True

    def debug(self, message):
        if self._debug:
            self.logger.debug(message)

    def info(self, message):
        self.logger.info(message)

    def error(self, message):
        self.logger.error(message)

    def warning(self, message):
        self.logger.warning(message)

    def critical(self, message):
        self.logger.critical(message)