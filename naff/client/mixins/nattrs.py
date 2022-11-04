import inspect
import typing
from logging import Logger


from naff.client import const
from naff.client.const import Sentinel

__all__ = ("Field", "Nattrs", "NOTSET")


class NotSet(Sentinel):
    def __bool__(self) -> bool:
        return False


NOTSET = NotSet()


class Field:
    def __init__(
        self,
        converter: typing.Callable = NOTSET,
        default: typing.Any = None,
        factory: typing.Callable = NOTSET,
        export: bool = True,
        repr: bool = False,
        export_converter: typing.Callable = NOTSET,
        **kwargs,
    ) -> None:
        self.converter = converter
        self.default = default
        self.factory = factory
        self.export = export
        self.repr = repr
        self.export_converter = export_converter

        if self.default and self.factory:
            self.default = NOTSET

        if kwargs.get("metadata"):
            # attrs compatibility
            self.export = not kwargs["metadata"].get("no_export", False)
            self.export_converter = kwargs["metadata"].get("export_converter", NOTSET)


T = typing.TypeVar("T")


class Nattrs:
    __default__: dict[str, Field] = NOTSET
    logger: Logger = Field(default=const.get_logger, export=False)

    @classmethod
    def __get_default(cls) -> dict[str, Field]:
        if cls.__default__:
            return cls.__default__

        cls.__default__ = dict(inspect.getmembers(cls, lambda x: isinstance(x, Field)))
        # cache the result so all subsequent calls are faster
        return cls.__default__

    @classmethod
    def from_dict(cls, payload: dict) -> T:
        payload = cls._process_dict(payload)
        return cls(**payload)

    def update_from_dict(self, payload: dict, *args) -> T:
        # todo: needs optimisation
        payload = self._process_dict(payload, *args)
        default_vars = self.__default__

        for key, value in payload.items():
            if field := default_vars.get(key, NOTSET):
                if field.converter:
                    value = field.converter(value)
            setattr(self, key, value)

        return self

    def __new__(cls, *args, **kwargs) -> T:
        # a convoluted way to take a payload and construct a class
        # allows an attrs-like developer experience, without the performance hit
        # ie: 120ms -> 20ms

        inst = super().__new__(cls)
        default_vars = cls.__get_default()
        slotted = hasattr(cls, "__slots__")

        for key, value in kwargs.items():
            if slotted:
                if key not in cls.__slots__:
                    continue
            if field := default_vars.get(key, NOTSET):
                if field.converter:
                    value = field.converter(value)
            setattr(inst, key, value)

        # default assignment
        for key, value in default_vars.items():
            if slotted:
                if key not in cls.__slots__:
                    continue
            if key in kwargs:
                # already assigned
                continue
            if value.default is not NOTSET:
                setattr(inst, key, value.default)
            elif value.factory is not NOTSET:
                setattr(inst, key, value.factory())

        return inst

    @classmethod
    def _process_dict(cls, payload: dict, *args) -> dict:
        """Logic to process dictionary payload received from discord api."""
        return payload

    def __repr__(self) -> str:
        var = self.__get_default()
        return f"{self.__class__.__name__}({', '.join(f'{k}={getattr(self, k)}' for k in var if var[k].repr)})"

    def to_dict(self) -> dict[str, typing.Any]:
        var = self.__get_default()
        payload = {}

        for key in var:
            if not var[key].export:
                continue
            value = getattr(self, key)
            if value is NOTSET:
                continue
            if var[key].export_converter:
                value = var[key].export_converter(value)
            payload[key] = value

        return payload
