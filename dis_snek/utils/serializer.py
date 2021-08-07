from datetime import datetime
from datetime import timezone

from attr import fields
from attr import has

no_export_meta = dict(no_export=True)


# def not_none(a, value):
#     return value is not None


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
        if value:
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
