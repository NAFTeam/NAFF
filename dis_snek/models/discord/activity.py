from typing import Optional, List

from dis_snek.client.mixins.serialization import DictSerializationMixin
from dis_snek.client.utils.attr_utils import define, field
from dis_snek.client.utils.serializer import dict_filter_none
from dis_snek.models.discord.asset import Asset
from dis_snek.models.discord.enums import ActivityType
from dis_snek.models.discord.snowflake import Snowflake_Type
from dis_snek.models.discord.timestamp import Timestamp

__all__ = ["Activity"]


@define()
class Activity(DictSerializationMixin):
    name: str = field(repr=True)
    type: ActivityType = field(repr=True, default=ActivityType.GAME)
    url: Optional[str] = field(repr=True, default=None)
    created_at: Timestamp = field(repr=True, default=None)
    timestamps: Timestamp = field(default=None)
    application_id: "Snowflake_Type" = field(default=None)
    details: Optional[str] = field(default=None)
    state: Optional[str] = field(default=None)
    emoji: Optional[str] = field(default=None)
    party: Optional[dict] = field(default=None)  # todo: Create party object
    assets: Optional[Asset] = field(default=None)
    secrets: Optional[str] = field(default=None)
    instance: Optional[bool] = field(default=False)
    flags: Optional[int] = field(default=None)  # todo: Activity Flags
    buttons: List[dict] = field(factory=list)  # todo: Activity Button Object

    @classmethod
    def create(cls, name: str, type: ActivityType = ActivityType.GAME, url: Optional[str] = None) -> "Activity":
        return cls(name=name, type=type, url=url)  # noqa

    def to_dict(self) -> dict:
        return dict_filter_none({"name": self.name, "type": self.type, "url": self.url})

    # todo: handle incoming presence data
