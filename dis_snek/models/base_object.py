from dis_snek.mixins.serialization import DictSerializationMixin
from typing import Any, Dict, TYPE_CHECKING
from dis_snek.utils.serializer import to_dict

import attr
from dis_snek.utils.attr_utils import define, field
from dis_snek.models.snowflake import Snowflake_Type, to_snowflake
from dis_snek.models.timestamp import Timestamp

if TYPE_CHECKING:
    from dis_snek.client import Snake


@define()
class SnowflakeObject:
    id: "Snowflake_Type" = field(repr=True, converter=to_snowflake)

    def __eq__(self, other):
        return self.id == other.id

    def __ne__(self, other):
        return self.id != other.id

    def __hash__(self):
        return int(self.id) << 32

    @property
    def created_at(self) -> "Timestamp":
        """
        Returns a timestamp representing the date-time this discord object was created
        :return:
        """
        return Timestamp.from_snowflake(self.id)


@define()
class DiscordObject(SnowflakeObject, DictSerializationMixin):
    _client: "Snake" = field()

    @classmethod
    def from_dict(cls, data: Dict[str, Any], client: "Snake"):
        data = cls.process_dict(data, client)
        return cls(client=client, **cls._filter_kwargs(data, cls._get_init_keys()))

    @classmethod
    def process_dict(cls, data: Dict[str, Any], client: "Snake") -> Dict[str, Any]:
        return super().process_dict(data)
