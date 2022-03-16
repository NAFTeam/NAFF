from typing import TYPE_CHECKING, Any, Dict, List, Type

import attrs

from dis_snek.client.const import T
from dis_snek.client.mixins.serialization import DictSerializationMixin
from dis_snek.client.utils.attr_utils import define, field
from dis_snek.client.utils.serializer import no_export_meta
from dis_snek.models.discord.snowflake import SnowflakeObject

if TYPE_CHECKING:
    from dis_snek.client import Snake

__all__ = ["ClientObject", "DiscordObject"]


@define(slots=False)
class ClientObject(DictSerializationMixin):
    _client: "Snake" = field(metadata=no_export_meta)

    @classmethod
    def _process_dict(cls, data: Dict[str, Any], client: "Snake") -> Dict[str, Any]:
        return super()._process_dict(data)

    @classmethod
    def from_dict(cls: Type[T], data: Dict[str, Any], client: "Snake") -> T:
        """
        Process and converts dictionary data received from discord api to object class instance.

        parameters:
            data: The json data received from discord api.

        """
        if isinstance(data, cls):
            return data
        data = cls._process_dict(data, client)

        parsed = {}
        for _field in attrs.fields(cls):
            field_name = _field.name.removeprefix("_")
            name = _field.metadata.get("data_key")
            if not name:
                name = field_name
            if name in data:
                value = data[name]
                if deserializer := _field.metadata.get("deserializer", None):
                    value = deserializer(value, data, client)
                parsed[field_name] = value

        print(parsed)
        return cls(**parsed, client=client)

    @classmethod
    def from_list(cls: Type[T], datas: List[Dict[str, Any]], client: "Snake") -> List[T]:
        return [cls.from_dict(data, client) for data in datas]

    def update_from_dict(self, data) -> None:
        data = self._process_dict(data, self._client)
        for key, value in self._filter_kwargs(data, self._get_keys()).items():
            # todo improve
            setattr(self, key, value)


@define(slots=False)
class DiscordObject(SnowflakeObject, ClientObject):
    pass
