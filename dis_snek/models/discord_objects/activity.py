from typing import Optional, List

import attr

from dis_snek.mixins.serialization import DictSerializationMixin
from dis_snek.models.discord_objects.asset import Asset
from dis_snek.models.enums import ActivityType
from dis_snek.models.snowflake import Snowflake_Type
from dis_snek.models.timestamp import Timestamp
from dis_snek.utils.attr_utils import define
from dis_snek.utils.serializer import dict_filter_none


@define()
class Activity(DictSerializationMixin):
    name: str = attr.ib()
    type: ActivityType = attr.ib(default=ActivityType.GAME)
    url: Optional[str] = attr.ib(default=None)
    created_at: Timestamp = attr.ib(default=None)
    timestamps: Timestamp = attr.ib(default=None)
    application_id: "Snowflake_Type" = attr.ib(default=None)
    details: Optional[str] = attr.ib(default=None)
    state: Optional[str] = attr.ib(default=None)
    emoji: Optional[str] = attr.ib(default=None)
    party: Optional[dict] = attr.ib(default=None)  # todo: Create party object
    assets: Optional[Asset] = attr.ib(default=None)
    secrets: Optional[str] = attr.ib(default=None)
    instance: Optional[bool] = attr.ib(default=False)
    flags: Optional[int] = attr.ib(default=None)  # todo: Activity Flags
    buttons: List[dict] = attr.ib(factory=list)  # todo: Activity Button Object

    @classmethod
    def create(cls, name: str, type: ActivityType = ActivityType.GAME, url: Optional[str] = None) -> "Activity":
        return cls(name=name, type=type, url=url)  # noqa

    def to_dict(self) -> dict:
        return dict_filter_none({"name": self.name, "type": self.type, "url": self.url})

    # todo: handle incoming presence data
