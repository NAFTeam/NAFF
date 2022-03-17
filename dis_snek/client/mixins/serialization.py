import logging
from typing import Any, Dict, List, TypeVar, Type, Callable, Union

import attrs

from dis_snek.client.const import logger_name, kwarg_spam, T
from dis_snek.client.utils.attr_utils import define
import dis_snek.client.utils.serializer as serializer

__all__ = ["DictSerializationMixin"]

log = logging.getLogger(logger_name)


def empty_deserializer(value, *args, **kwargs):
    return value


@define(slots=False)
class DictSerializationMixin:
    @classmethod
    def _get_deserializers(cls: Type[T]) -> Dict[str, Callable]:
        if (deserializers := getattr(cls, "_deserializers", None)) is None:
            deserializers = {}
            for field in attrs.fields(cls):
                name = field.metadata.get("data_key", None) or field.name
                deserializers[name] = field.metadata.get("deserializer", None) or empty_deserializer
            setattr(cls, "_deserializers", deserializers)
        return deserializers

    @classmethod
    def _get_init_deserializers(cls: Type[T]) -> Dict[str, Callable]:
        if (deserializers := getattr(cls, "_init_deserializers", None)) is None:
            fields = attrs.fields_dict(cls)
            deserializers = {k.removeprefix("_"): v for k, v in cls._get_deserializers().items() if fields[k].init}
            setattr(cls, "_init_deserializers", deserializers)
        return deserializers

    @classmethod
    def _process_dict(cls, data: Dict[str, Any], **kwargs) -> Dict[str, Any]:
        """
        Process dictionary data received from discord api. Does cleanup and other checks to data.

        parameters:
            data: The dictionary data received from discord api.

        returns:
            The processed dictionary. Ready to be converted into object class.

        """
        return data

    @classmethod
    def from_dict(cls: Type[T], data: Union[Dict[str, Any], T], **kwargs) -> T:
        """
        Process and converts dictionary data received from discord api to object class instance.

        parameters:
            data: The json data received from discord api.

        """
        if isinstance(data, cls):
            return data
        data |= kwargs
        data = cls._process_dict(data, **kwargs)
        return cls(**{k: v(data[k], data, **kwargs) for k, v in cls._get_init_deserializers().items() if k in data})

    @classmethod
    def from_list(cls: Type[T], data_list: List[Dict[str, Any]], **kwargs) -> List[T]:
        """
        Process and converts list data received from discord api to object class instances.

        parameters:
            data: The json data received from discord api.

        """
        return [cls.from_dict(data, **kwargs) for data in data_list]

    def update_from_dict(self: T, data: Dict[str, Any], **kwargs) -> T:
        """Updates object attribute(s) with new json data received from discord api."""
        data |= kwargs
        data = self._process_dict(data, **kwargs)
        for key, value in self._get_deserializers().items():
            if key in data:
                setattr(self, key, value(data[key], data, **kwargs))
        return self

    def _check_object(self) -> None:
        """Logic to check object properties just before export to json data for sending to discord api."""
        pass

    def to_dict(self) -> Dict[str, Any]:
        """
        Exports object into dictionary representation, ready to be sent to discord api.

        returns:
            The exported dictionary.

        """
        self._check_object()
        return serializer.to_dict(self)
