import logging
from functools import partial
from typing import Any, Dict, Callable

import attrs
from dis_snek.client.const import logger_name, MISSING, T, Absent

__all__ = ["define", "field", "docs", "str_validator"]

log = logging.getLogger(logger_name)

class_defaults = {
    "eq": False,
    "order": False,
    "hash": False,
    "slots": True,
    "kw_only": True,
}
field_defaults = {"repr": False}


define = partial(attrs.define, **class_defaults)  # type: ignore


def field(
    data_key: Absent[str] = MISSING,
    deserializer: Absent[Callable] = MISSING,
    docs: Absent[str] = MISSING,
    no_export: Absent[bool] = MISSING,
    metadata: Absent[dict] = MISSING,
    **kwargs,
) -> attrs.Attribute:
    data = {
        "data_key": data_key,
        "deserializer": deserializer,
        "docs": docs,
        "no_export": no_export,
    }
    if metadata:
        data |= metadata
    return attrs.field(metadata=data, **kwargs)


def copy_converter(value: T) -> T:
    if isinstance(value, (list, set)):
        return value.copy()
    return value


def docs(doc_string: str) -> Dict[str, str]:
    """Makes it easier to quickly type attr documentation."""
    return {"docs": doc_string}


# def converter(attribute):
#     def decorator(func):
#         attribute.converter = func
#         return staticmethod(func)
#
#     return decorator


def str_validator(self, attribute: attrs.Attribute, value: Any) -> None:
    if not isinstance(value, str):
        if value is MISSING:
            return
        setattr(self, attribute.name, str(value))
        log.warning(
            f"Value of {attribute.name} has been automatically converted to a string. Please use strings in future.\n"
            "Note: Discord will always return value as a string"
        )
