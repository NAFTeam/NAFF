from dis_snek.const import kwarg_spam
from dis_snek.utils.serializer import to_dict
from typing import Any, Dict
import attr


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
        unused = {k: v for k, v in kwargs_dict.items() if k not in keys}
        if unused and kwarg_spam:
            print("Unused kwargs:", cls.__name__, unused)  # for debug
        return {k: v for k, v in kwargs_dict.items() if k in keys}

    @classmethod
    def from_dict(cls, data: Dict[str, Any]):
        data = cls._process_dict(data)
        return cls(**cls._filter_kwargs(data, cls._get_init_keys()))

    @classmethod
    def _process_dict(cls, data: Dict[str, Any]) -> Dict[str, Any]:
        return data

    def update_from_dict(self, data):
        data = self._process_dict(data, self._client)
        for key, value in self._filter_kwargs(data, self._get_keys()).items():
            # todo improve
            setattr(self, key, value)

    def _check_object(self):
        pass

    def to_dict(self) -> Dict[str, Any]:
        self._check_object()
        return to_dict(self)
