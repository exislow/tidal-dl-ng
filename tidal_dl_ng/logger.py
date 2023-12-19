import logging
import sys

import coloredlogs
from PySide6 import QtCore


class XStream(QtCore.QObject):
    _stdout = None
    _stderr = None
    messageWritten = QtCore.Signal(str)

    def flush(self):
        pass

    def fileno(self):
        return -1

    def write(self, msg):
        if not self.signalsBlocked():
            self.messageWritten.emit(msg)

    @staticmethod
    def stdout():
        if not XStream._stdout:
            XStream._stdout = XStream()
            sys.stdout = XStream._stdout
        return XStream._stdout

    @staticmethod
    def stderr():
        if not XStream._stderr:
            XStream._stderr = XStream()
            sys.stderr = XStream._stderr
        return XStream._stderr


class QtHandler(logging.Handler):
    def __init__(self):
        logging.Handler.__init__(self)

    def emit(self, record):
        record = self.format(record)

        if record:
            # originally: XStream.stdout().write("{}\n".format(record))
            XStream.stdout().write("%s\n" % record)


logger_gui = logging.getLogger(__name__)
handler_qt: QtHandler = QtHandler()
# log_fmt: str = "[%(asctime)s] %(levelname)s: %(message)s"
log_fmt: str = "> %(message)s"
# formatter = logging.Formatter(log_fmt)
formatter = coloredlogs.ColoredFormatter(fmt=log_fmt)
handler_qt.setFormatter(formatter)
logger_gui.addHandler(handler_qt)
logger_gui.setLevel(logging.DEBUG)

logger_cli = logging.getLogger(__name__)
handler_stream: logging.StreamHandler = logging.StreamHandler()
formatter = coloredlogs.ColoredFormatter(fmt=log_fmt)
handler_stream.setFormatter(formatter)
logger_cli.addHandler(handler_stream)
logger_cli.setLevel(logging.DEBUG)
