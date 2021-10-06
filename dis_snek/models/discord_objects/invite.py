from enum import IntEnum
from typing import TYPE_CHECKING, List, Optional, Union, Dict, Any

from attr.converters import optional as optional_c

from dis_snek.mixins.serialization import DictSerializationMixin
from dis_snek.models.discord import ClientObject
from dis_snek.models.snowflake import to_snowflake
from dis_snek.models.timestamp import Timestamp
from dis_snek.utils.attr_utils import define, field
from dis_snek.utils.converters import timestamp_converter

if TYPE_CHECKING:
    from dis_snek.client import Snake
    from dis_snek.models.discord_objects.user import Member, User
    from dis_snek.models.snowflake import Snowflake_Type
    from dis_snek.models.discord_objects.channel import BaseChannel
    from dis_snek.models.discord_objects.guild import Guild


class InviteTargetTypes(IntEnum):
    STREAM = 1
    EMBEDDED_APPLICATION = 2


@define()
class InviteStageInstance(DictSerializationMixin):
    members: List["Member"] = field()  # TODO Get from cache
    participant_count: int = field()
    speaker_count: int = field()
    topic: str = field()


@define()
class InviteMetadata(DictSerializationMixin):  # TODO This should be part of invite.
    uses: int = field()
    max_uses: int = field()
    max_age: int = field()
    temporary: bool = field(default=False)
    created_at: Timestamp = field(converter=timestamp_converter)


@define()
class Invite(ClientObject):
    code: str = field()
    target_type: Optional[Union[InviteTargetTypes, int]] = field(converter=optional_c(InviteTargetTypes))
    approximate_presence_count: Optional[int] = field(default=-1)
    approximate_member_count: Optional[int] = field(default=-1)
    target_application: Optional[dict] = field(default=None)  # TODO Partial application
    expires_at: Optional[Timestamp] = field(converter=optional_c(timestamp_converter))
    stage_instance: Optional[InviteStageInstance] = field(default=None)

    _guild_id: Optional["Snowflake_Type"] = field(default=None, converter=optional_c(to_snowflake))
    _channel_id: "Snowflake_Type" = field(converter=to_snowflake)
    _inviter_id: Optional["Snowflake_Type"] = field(default=None, converter=optional_c(to_snowflake))
    _target_user_id: Optional["Snowflake_Type"] = field(default=None, converter=optional_c(to_snowflake))

    # todo have these attributes populated on creation of this class
    guild: "Guild" = field(default=None)
    channel: "BaseChannel" = field(default=None)
    inviter: "User" = field(default=None)
    target_user: "User" = field(default=None)

    @classmethod
    def _process_dict(cls, data: Dict[str, Any], client: "Snake") -> Dict[str, Any]:
        if "stage_instance" in data:
            data["stage_instance"] = InviteStageInstance.from_dict(data)

        # TODO Convert target_application

        return data

    @property
    def link(self):
        return f"https://discord.gg/{self.code}"
