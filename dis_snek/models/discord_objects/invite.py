from enum import IntEnum
from typing import TYPE_CHECKING, List, Optional, Union

from attr.converters import optional as optional_c

from dis_snek.mixins.serialization import DictSerializationMixin
from dis_snek.models.timestamp import Timestamp
from dis_snek.utils.attr_utils import define, field
from dis_snek.utils.converters import timestamp_converter

if TYPE_CHECKING:
    from dis_snek.models.discord_objects.channel import Channel
    from dis_snek.models.discord_objects.guild import Guild
    from dis_snek.models.discord_objects.user import User, Member


class InviteTargetTypes(IntEnum):
    STREAM = 1
    EMBEDDED_APPLICATION = 2


@define(slots=True, kw_only=True)
class InviteStageInstance(DictSerializationMixin):
    members: List["Member"] = field()
    participant_count: int = field()
    speaker_count: int = field()
    topic: str = field()


@define(slots=True, kw_only=True)
class InviteMetadata(DictSerializationMixin):
    uses: int = field()
    max_uses: int = field()
    max_age: int = field()
    temporary: bool = field(default=False)
    created_at: Timestamp = field(converter=timestamp_converter)


@define(slots=True, kw_only=True)
class Invite(DictSerializationMixin):
    code: str = field()
    guild: Optional["Guild"] = field(default=None)
    channel: "Channel" = field()
    inviter: Optional["User"] = field()
    target_type: Optional[Union[InviteTargetTypes, int]] = field(converter=optional_c(InviteTargetTypes))
    target_user: Optional["User"] = field()
    approximate_presence_count: Optional[int] = field()
    approximate_member_count: Optional[int] = field()
    expires_at: Optional[Timestamp] = field(converter=optional_c(timestamp_converter))
    stage_instance: Optional[InviteStageInstance] = field()
