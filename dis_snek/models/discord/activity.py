from typing import Optional, List

from dis_snek.client.mixins.serialization import DictSerializationMixin
from dis_snek.client.utils.attr_utils import define, field
from dis_snek.client.utils.converters import timestamp_converter, optional
from dis_snek.client.utils.serializer import dict_filter_none
from dis_snek.models.discord.emoji import PartialEmoji
from dis_snek.models.discord.enums import ActivityType, ActivityFlags
from dis_snek.models.discord.snowflake import Snowflake_Type
from dis_snek.models.discord.timestamp import Timestamp

__all__ = ["Activity"]


@define()
class ActivityTimestamps(DictSerializationMixin):
    start: Optional[Timestamp] = field(default=None, converter=optional(timestamp_converter))
    end: Optional[Timestamp] = field(default=None, converter=optional(timestamp_converter))


@define()
class ActivityParty(DictSerializationMixin):
    id: Optional[str] = field(default=None)
    size: Optional[List[int]] = field(default=None)


@define()
class ActivityAssets(DictSerializationMixin):
    large_image: Optional[str] = field(default=None)
    large_text: Optional[str] = field(default=None)
    small_image: Optional[str] = field(default=None)
    small_text: Optional[str] = field(default=None)


@define()
class ActivitySecrets(DictSerializationMixin):
    join: Optional[str] = field(default=None)
    spectate: Optional[str] = field(default=None)
    match: Optional[str] = field(default=None)


@define()
class ActivityButton(DictSerializationMixin):
    label: str = field()
    url: str = field()


@define(kw_only=False)
class Activity(DictSerializationMixin):
    name: str = field(repr=True)
    type: ActivityType = field(repr=True, default=ActivityType.GAME)
    url: Optional[str] = field(repr=True, default=None)
    created_at: Optional[Timestamp] = field(repr=True, default=None, converter=optional(timestamp_converter))
    timestamps: Optional[ActivityTimestamps] = field(default=None, converter=optional(ActivityTimestamps.from_dict))
    application_id: "Snowflake_Type" = field(default=None)
    details: Optional[str] = field(default=None)
    state: Optional[str] = field(default=None)
    emoji: Optional[PartialEmoji] = field(default=None, converter=optional(PartialEmoji.from_dict))
    party: Optional[ActivityParty] = field(default=None, converter=optional(ActivityParty.from_dict))
    assets: Optional[ActivityAssets] = field(default=None, converter=optional(ActivityAssets.from_dict))
    secrets: Optional[ActivitySecrets] = field(default=None, converter=optional(ActivitySecrets.from_dict))
    instance: Optional[bool] = field(default=False)
    flags: Optional[ActivityFlags] = field(default=None, converter=optional(ActivityFlags))
    buttons: List[ActivitySecrets] = field(factory=list, converter=optional(ActivityButton.from_list))

    @classmethod
    def create(cls, name: str, type: ActivityType = ActivityType.GAME, url: Optional[str] = None) -> "Activity":
        return cls(name=name, type=type, url=url)  # noqa

    def to_dict(self) -> dict:
        return dict_filter_none({"name": self.name, "type": self.type, "url": self.url})

    # todo: handle incoming presence data
