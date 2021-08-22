import logging
from typing import Any, Dict

import attr

from dis_snek.const import logger_name
from dis_snek.utils.serializer import to_dict


log = logging.getLogger(logger_name)


default_kwargs = dict(kw_only=True, on_setattr=[attr.setters.convert, attr.setters.validate])


def converter(attribute):
    def decorator(func):
        attribute.converter = func
        return staticmethod(func)

    return decorator


def str_validator(self, attribute: attr.Attribute, value: Any):
    if not isinstance(value, str):
        setattr(self, attribute.name, str(value))
        log.warning(
            f"Value of {attribute.name} has been automatically converted to a string. Please use strings in future.\n"
            "Note: Discord will always return value as a string"
        )


class DictSerializationMixin:
    @classmethod
    def _get_keys(cls):
        if (keys := getattr(cls, "_keys", None)) is None:
            keys = frozenset(field.name for field in attr.fields(cls))
            setattr(cls, "_keys", keys)
        return keys

    @classmethod
    def _get_init_keys(cls):
        if (init_keys := getattr(cls, "_init_keys", None)) is None:
            init_keys = frozenset(field.name.removeprefix("_") for field in attr.fields(cls) if field.init)
            setattr(cls, "_init_keys", init_keys)
        return init_keys

    @classmethod
    def _filter_kwargs(cls, kwargs_dict: dict, keys: frozenset):
        return {k: v for k, v in kwargs_dict.items() if k in keys}

    @classmethod
    def from_dict(cls, data: Dict[str, Any], client: Any):
        data = cls.process_dict(data, client)
        return cls(client=client, **cls._filter_kwargs(data, cls._get_init_keys()))

    @classmethod
    def process_dict(cls, data, client):
        return data

    def update_from_dict(self, data):
        data = self.process_dict(data, self._client)
        for key, value in self._filter_kwargs(data, self._get_keys()).items():
            setattr(self, key, value)

    def to_dict(self):
        return to_dict(self)
