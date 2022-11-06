import inspect
import typing
from logging import Logger


from naff.client import const
from naff.client.const import Sentinel, MISSING

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
        convert_if_none: bool = False,
        convert_if_missing: bool = False,
        **kwargs,
    ) -> None:
        self.converter = converter
        self.default = default
        self.factory = factory
        self.export = export
        self.repr = repr
        self.export_converter = export_converter
        self.convert_if_none = convert_if_none
        self.convert_if_missing = convert_if_missing

        if self.default and self.factory:
            self.default = NOTSET

        if kwargs.get("metadata"):
            # attrs compatibility
            self.export = not kwargs["metadata"].get("no_export", False)
            self.export_converter = kwargs["metadata"].get("export_converter", NOTSET)

    def __bool__(self) -> bool:
        return False


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

    @classmethod
    def from_list(cls, payload: list[dict]) -> list[T]:
        return [cls.from_dict(x) for x in payload]

    def update_from_dict(self, payload: dict, *args) -> T:
        # todo: needs optimisation
        payload = self._process_dict(payload, *args)
        default_vars = self.__default__

        for key in payload:
            value = payload[key]
            if key in default_vars:
                field = default_vars[key]
                if field.converter:
                    if value is not None and value is not MISSING:
                        value = field.converter(value)
                    elif (value is None and field.convert_if_none) or (value is MISSING and field.convert_if_missing):
                        value = field.converter(value)
            setattr(self, key, value)

        return self

    def __new__(cls, **kwargs) -> T:
        # a convoluted way to take a payload and construct a class
        # allows an attrs-like developer experience, without the performance hit
        # ie: 120ms -> 20ms

        inst = object.__new__(cls)
        default_vars = cls.__get_default()
        slotted = hasattr(cls, "__slots__")

        for key in kwargs:
            if slotted and key not in cls.__slots__:
                continue
            value = kwargs[key]
            if (field := default_vars.get(key, NOTSET)) is not NOTSET:
                if field.converter:
                    if value is not None and value is not MISSING:
                        value = field.converter(value)
                    elif (value is None and field.convert_if_none) or (value is MISSING and field.convert_if_missing):
                        value = field.converter(value)
            setattr(inst, key, value)

        # default assignment
        for key in default_vars:
            if key in kwargs:
                # already assigned
                continue
            if slotted and key not in cls.__slots__:
                continue
            value = default_vars[key]
            if value.default is not NOTSET:
                setattr(inst, key, value.default)
            elif value.factory is not NOTSET:
                setattr(inst, key, value.factory())

        if hasattr(inst.__class__, "__post_init__"):
            inst.__post_init__()  # noqa
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
