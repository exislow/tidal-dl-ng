from collections.abc import Callable


class LoggerWrapped:
    fn_print: Callable = None

    def __init__(self, fn_print: Callable):
        self.fn_print = fn_print

    def debug(self, value):
        self.fn_print(value)

    def warning(self, value):
        self.fn_print(value)

    def info(self, value):
        self.fn_print(value)

    def error(self, value):
        self.fn_print(value)

    def critical(self, value):
        self.fn_print(value)

    def exception(self, value):
        self.fn_print(value)
