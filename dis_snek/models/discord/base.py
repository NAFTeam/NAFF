from typing import TYPE_CHECKING, Any, Dict, List, Type

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
        data = cls._process_dict(data, client)
        return cls(client=client, **cls._filter_kwargs(data, cls._get_init_keys()))

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
