from typing import TYPE_CHECKING, Any, Dict, List

import attr

from dis_snek.mixins.serialization import DictSerializationMixin
from dis_snek.models.snowflake import SnowflakeObject
from dis_snek.utils.attr_utils import field
from dis_snek.utils.serializer import no_export_meta

if TYPE_CHECKING:
    from dis_snek.client import Snake


@attr.s()
class ClientObject(DictSerializationMixin):
    _client: "Snake" = field(metadata=no_export_meta)

    @classmethod
    def _process_dict(cls, data: Dict[str, Any], client: "Snake") -> Dict[str, Any]:
        return super()._process_dict(data)

    @classmethod
    def from_dict(cls, data: Dict[str, Any], client: "Snake"):
        data = cls._process_dict(data, client)
        return cls(client=client, **cls._filter_kwargs(data, cls._get_init_keys()))

    @classmethod
    def from_list(cls, datas: List[Dict[str, Any]], client: "Snake"):
        return [cls.from_dict(data, client) for data in datas]

    def update_from_dict(self, data):
        data = self._process_dict(data, self._client)
        for key, value in self._filter_kwargs(data, self._get_keys()).items():
            # todo improve
            setattr(self, key, value)


@attr.s()
class DiscordObject(SnowflakeObject, ClientObject):
    pass
