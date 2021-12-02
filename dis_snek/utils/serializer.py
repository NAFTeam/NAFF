from base64 import b64encode
from ctypes import Union
from datetime import datetime, timezone
from io import IOBase
from pathlib import Path
from typing import Optional

from attr import fields, has

from dis_snek.const import MISSING


no_export_meta = dict(no_export=True)


def export_converter(converter) -> dict:
    return dict(export_converter=converter)


def to_dict(inst):
    if (converter := getattr(inst, "as_dict", None)) is not None:
        return converter()

    attrs = fields(inst.__class__)
    d = dict()

    for a in attrs:
        if a.metadata.get("no_export", False):
            continue

        raw_value = getattr(inst, a.name)
        if raw_value is MISSING:
            continue

        if (c := a.metadata.get("export_converter", None)) is not None:
            value = c(raw_value)
        else:
            value = _to_dict_any(raw_value)

        if isinstance(value, (bool, int)) or value:
            d[a.name] = value

    return d


def _to_dict_any(inst):
    if has(inst.__class__):
        return to_dict(inst)
    elif isinstance(inst, dict):
        return {key: _to_dict_any(value) for key, value in inst.items()}
    elif isinstance(inst, (list, tuple, set, frozenset)):
        return [_to_dict_any(item) for item in inst]
    elif isinstance(inst, datetime):
        if inst.tzinfo:
            return inst.isoformat()
        else:
            return inst.replace(tzinfo=timezone.utc).isoformat()
    else:
        return inst


def dict_filter_none(data: dict) -> dict:
    return {k: v for k, v in data.items() if v is not None}


def dict_filter_missing(data: dict) -> dict:
    return {k: v for k, v in data.items() if v is not MISSING}


def to_image_data(imagefile) -> Optional[str]:
    if isinstance(imagefile, IOBase):
        image_data = imagefile.read()
    elif isinstance(imagefile, (str, Path)):
        with open(imagefile, "rb") as image_buffer:
            image_data = image_buffer.read()
    else:
        return imagefile

    mimetype = _get_file_mimetype(image_data)
    encoded_image = b64encode(image_data).decode("ascii")

    return f"data:{mimetype};base64,{encoded_image}"


def _get_file_mimetype(filedata: bytes):
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
