from typing import TYPE_CHECKING, Any, Dict, List, Type

from naff.client.const import T
from naff.client.mixins.serialization import DictSerializationMixin
from naff.client.utils.attr_utils import define, field
from naff.client.utils.serializer import no_export_meta
from naff.models.discord.snowflake import SnowflakeObject

if TYPE_CHECKING:
    from naff.client import Client

__all__ = ("ClientObject", "DiscordObject")


@define(slots=False)
class ClientObject(DictSerializationMixin):
    """Serializable object that requires client reference."""

    _client: "Client" = field(metadata=no_export_meta)

    @classmethod
    def _process_dict(cls, data: Dict[str, Any], client: "Client") -> Dict[str, Any]:
        return super()._process_dict(data)

    @classmethod
    def from_dict(cls: Type[T], data: Dict[str, Any], client: "Client") -> T:
        data = cls._process_dict(data, client)
        return cls(client=client, **cls._filter_kwargs(data, cls._get_init_keys()))

    @classmethod
    def from_list(cls: Type[T], datas: List[Dict[str, Any]], client: "Client") -> List[T]:
        return [cls.from_dict(data, client) for data in datas]

    def update_from_dict(self, data) -> T:
        data = self._process_dict(data, self._client)
        for key, value in self._filter_kwargs(data, self._get_keys()).items():
            # todo improve
            setattr(self, key, value)

        return self


@define(slots=False)
class DiscordObject(SnowflakeObject, ClientObject):
    pass
