import attr


def converter(attribute):
    def decorator(func):
        attribute.converter = func
        return staticmethod(func)
    return decorator


class IgnoreExtraKeysMixin:
    @classmethod
    def _get_keys(cls):
        if (keys := getattr(cls, "_keys", None)) is None:
            keys = frozenset(field.name.removeprefix("_") for field in attr.fields(cls))
            setattr(cls, "_keys", keys)
        return keys

    @classmethod
    def _filter_kwargs(cls, kwargs_dict: dict):
        keys = cls._get_keys()
        return {k: v for k, v in kwargs_dict.items() if k in keys}
