import logging
from functools import partial
from typing import Any

import attr
from dis_snek.const import logger_name


log = logging.getLogger(logger_name)


class_defaults = dict(
    eq=False,
    order=False,
    hash=False,
    slots=True,
    kw_only=True,
    on_setattr=[attr.setters.convert, attr.setters.validate],
)
field_defaults = dict(repr=False)


define = partial(attr.define, **class_defaults)
field = partial(attr.field, **field_defaults)


def copy_converter(value):
    if isinstance(value, (list, set)):
        return value.copy()
    return value


# def converter(attribute):
#     def decorator(func):
#         attribute.converter = func
#         return staticmethod(func)
#
#     return decorator


def str_validator(self, attribute: attr.Attribute, value: Any):
    if not isinstance(value, str):
        setattr(self, attribute.name, str(value))
        log.warning(
            f"Value of {attribute.name} has been automatically converted to a string. Please use strings in future.\n"
            "Note: Discord will always return value as a string"
        )
