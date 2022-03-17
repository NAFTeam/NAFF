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


# noinspection PyMethodOverriding
@define(slots=False)
class ClientObject(DictSerializationMixin):
    _client: "Snake" = field(metadata=no_export_meta)

    @classmethod
    def _process_dict(cls, data: Dict[str, Any], client: "Snake", **kwargs) -> Dict[str, Any]:
        return super()._process_dict(data)

    @classmethod
    def from_dict(cls: Type[T], data: Dict[str, Any], client, **kwargs) -> T:
        """
        Process and converts dictionary data received from discord api to object class instance.

        parameters:
            data: The json data received from discord api.

        """
        return super().from_dict(data, client=client, **kwargs)

    @classmethod
    def from_list(cls: Type[T], data_list: List[Dict[str, Any]], client, **kwargs) -> List[T]:
        """
        Process and converts list data received from discord api to object class instances.

        parameters:
            data: The json data received from discord api.

        """
        return super().from_list(data_list, client=client, **kwargs)

    def update_from_dict(self: T, data: Dict[str, Any], **kwargs) -> T:
        return super().update_from_dict(data, client=self._client, **kwargs)


@define(slots=False)
class DiscordObject(SnowflakeObject, ClientObject):
    pass
