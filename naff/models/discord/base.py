from typing import TYPE_CHECKING, Any, Dict, List, Type

from typing_extensions import dataclass_transform

from naff.client.const import T
from naff.client.mixins.nattrs import Nattrs, Field
from naff.models.discord.snowflake import SnowflakeObject

if TYPE_CHECKING:
    from naff.client import Client

__all__ = ("ClientObject", "DiscordObject")


@dataclass_transform()
class ClientObject(Nattrs):
    """Serializable object that requires client reference."""

    _client: "Client" = Field(export=False)

    @classmethod
    def from_dict(cls: Type[T], payload: Dict[str, Any], client: "Client") -> T:
        payload = cls._process_dict(payload, client)

        instance = cls(**payload)
        instance._client = client
        return instance

    @classmethod
    def from_list(cls: Type[T], payload: list[dict[str, Any]], client: "Client") -> List[T]:
        return [cls.from_dict(data, client) for data in payload]

    @classmethod
    def _process_dict(cls, payload: dict, client: "Client") -> dict:
        return payload

    def update_from_dict(self, data, *args) -> T:
        return super().update_from_dict(data, self._client)


@dataclass_transform()
class DiscordObject(SnowflakeObject, ClientObject):
    pass
