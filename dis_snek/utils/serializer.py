from base64 import b64encode, encode
from datetime import datetime, timezone
from io import IOBase
from typing import Union

from attr import fields, has


no_export_meta = dict(no_export=True)


def to_dict(inst):
    if (converter := getattr(inst, "as_dict", None)) is not None:
        return converter()

    attrs = fields(inst.__class__)
    d = dict()

    for a in attrs:
        if a.metadata.get("no_export", False):
            continue

        raw_value = getattr(inst, a.name)
        value = _to_dict_any(raw_value)
        if isinstance(value, bool) or value:
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


def to_image_data(imagefile):
    if issubclass(type(imagefile), IOBase):
        image_data = imagefile.read()
    else:
        with open(imagefile, 'rb') as opened_image:
            image_data = opened_image.read()

    mimetype = _get_file_mimetype(image_data)
    encoded_image = b64encode(image_data).decode('ascii')

    return f"data:{mimetype};base64,{encoded_image}"


def _get_file_mimetype(filedata: bytes):
    header_byte = filedata[0:3].hex()
    print("header_byte ->", header_byte, type(header_byte))

    if header_byte == "474946":
        return "image/gif"
    elif header_byte == "89504e":
        return "image/png"
    elif header_byte == "ffd8ff":
        return "image/jpeg"
    else:
        return "application/octet-stream"
