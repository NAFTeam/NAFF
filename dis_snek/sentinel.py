import inspect
from typing import Optional


class Singleton(type):
    _instances = {}

    def __call__(cls, *args, **kwargs):
        if cls not in cls._instances:
            cls._instances[cls] = super(Singleton, cls).__call__(*args, **kwargs)
        return cls._instances[cls]

    def __copy__(self):
        return self

    def __deepcopy__(self):
        return self


class Sentinel(metaclass=Singleton):
    @staticmethod
    def _get_caller_module() -> str:
        stack = inspect.stack()

        caller = stack[2][0]
        return caller.f_globals.get("__name__")

    def __init__(self):
        self.__module__ = self._get_caller_module()
        self.name = type(self).__name__

    def __repr__(self):
        return self.name

    def __reduce__(self):
        return self.name
