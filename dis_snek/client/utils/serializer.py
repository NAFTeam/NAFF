import inspect
from base64 import b64encode
from datetime import datetime, timezone
from functools import partial
from io import IOBase
from pathlib import Path
from typing import Optional, Type, Dict, Callable, Any

from attrs import fields, has

from dis_snek.client.const import MISSING, T
import dis_snek.models as models

__all__ = [
    "no_export_meta",
    "export_converter",
    "attrs_serializer",
    "dict_filter_none",
    "dict_filter_missing",
    "to_image_data",
]

no_export_meta = {"no_export": True}  # TODO: remove this


def export_converter(converter) -> dict:  # TODO: remove this
    return {"export_converter": converter}


def to_value(value, data, **kwargs):
    return value


def to_object(cls: Type[T]) -> T:
    """
    Deserialize a class from a dict.

    Args:
        cls: The class to deserialize

    Returns:
        The deserialized object
    """

    def inner(value: dict, data: Dict[str, Any], **kwargs) -> T:
        from_dict = getattr(cls, "from_dict", None) or partial(default_deserializer, cls)
        return cls.from_dict(value, **kwargs)

    return inner


def attrs_deserializer(cls, data, **kwargs):
    if isinstance(data, cls):
        return data
    data |= kwargs
    data = cls._process_dict(data, **kwargs)
    return cls(
        **{
            n: s(data[k], data, **kwargs) if s else data[k]
            for n, (k, s) in _get_init_deserializers(cls).items()
            if k in data
        }
    )


def default_deserializer(cls, data, **kwargs):
    if has(cls):
        return attrs_deserializer(cls, data, **kwargs)
    return cls(**data, **kwargs)


def _get_deserializers(cls: Type[T]) -> Dict[str, Callable]:
    if (deserializers := getattr(cls, "_deserializers", None)) is None:
        deserializers = {}
        for field in fields(cls):
            name = field.metadata.get("data_key", None) or field.name
            deserializers[field.name] = (name, field.metadata.get("deserializer", None))
        setattr(cls, "_deserializers", deserializers)
    return deserializers


def _get_init_deserializers(cls: Type[T]) -> Dict[str, Callable]:
    if (deserializers := getattr(cls, "_init_deserializers", None)) is None:
        deserializers = {}
        for field in fields(cls):
            if not field.init:
                continue
            field_name = field.name.removeprefix("_")
            name = field.metadata.get("data_key", None) or field_name
            deserializers[field_name] = (name, field.metadata.get("deserializer", None))
        setattr(cls, "_init_deserializers", deserializers)
    return deserializers


def attrs_serializer(inst) -> dict:
    serialized = {}
    s = _get_serializers(inst.__class__)
    for field_name, serializer in s.items():
        raw_value = getattr(inst, field_name)
        if raw_value is MISSING:
            continue
        value = serializer(raw_value)
        if isinstance(value, (bool, int)) or value:
            serialized[field_name] = value
    return serialized


def default_serializer(inst: T) -> dict | list | str | T:
    if has(inst.__class__):
        return attrs_serializer(inst)
    elif isinstance(inst, dict):
        return {key: default_serializer(value) for key, value in inst.items()}
    elif isinstance(inst, (list, tuple, set, frozenset)):
        return [default_serializer(item) for item in inst]
    elif isinstance(inst, datetime):
        if inst.tzinfo:
            return inst.isoformat()
        else:
            return inst.replace(tzinfo=timezone.utc).isoformat()
    else:
        return inst


def _get_serializers(cls):
    if (serializers := getattr(cls, "_serializers", None)) is None:
        serializers = {}
        for field in fields(cls):
            if not field.metadata.get("serialize", True) or field.metadata.get(
                "no_export", False
            ):  # TODO: remove no_export fallback
                continue

            if (
                c := field.metadata.get("export_converter", None)
            ) is not None:  # TODO: remove export_converter fallback
                serializers[field.name] = c
            else:
                serializers[field.name] = default_serializer
        setattr(cls, "_serializers", serializers)

    return serializers


def dict_filter_none(data: dict) -> dict:
    return {k: v for k, v in data.items() if v is not None}


def dict_filter_missing(data: dict) -> dict:
    return {k: v for k, v in data.items() if v is not MISSING}


def to_image_data(imagefile: Optional["models.UPLOADABLE_TYPE"]) -> Optional[str]:
    match imagefile:
        case bytes():
            image_data = imagefile
        case IOBase():
            image_data = imagefile.read()
        case Path() | str():
            with open(str(imagefile), "rb") as image_buffer:
                image_data = image_buffer.read()
        case models.File():
            with imagefile.open_file() as image_buffer:
                image_data = image_buffer.read()
        case _:
            return imagefile

    mimetype = _get_file_mimetype(image_data)
    encoded_image = b64encode(image_data).decode("ascii")

    return f"data:{mimetype};base64,{encoded_image}"


def _get_file_mimetype(filedata: bytes) -> str:
    if filedata.startswith((b"GIF87a", b"GIF89a")):
        return "image/gif"
    elif filedata.startswith(b"\x89PNG\x0D\x0A\x1A\x0A"):
        return "image/png"
    elif filedata.startswith(b"\xff\xd8\xff"):
        return "image/jpeg"
    elif filedata[0:4] == b"RIFF" and filedata[8:12] == b"WEBP":
        return "image/webp"
    else:
        return "application/octet-stream"
