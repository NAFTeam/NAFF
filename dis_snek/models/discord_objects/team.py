from typing import TYPE_CHECKING, List, Optional

import attr

from dis_snek.models.discord import DiscordObject
from dis_snek.models.enums import TeamMembershipState
from dis_snek.utils.attr_utils import define

if TYPE_CHECKING:
    from dis_snek.models.discord_objects.user import User
    from dis_snek.models.snowflake import Snowflake_Type


@define()
class TeamMember:
    membership_state: TeamMembershipState = attr.ib(converter=TeamMembershipState)
    permissions: List[str] = attr.ib(default=["*"])
    team_id: "Snowflake_Type" = attr.ib()
    user: "User" = attr.ib()  # TODO: cache partial user (avatar, discrim, id, username)


@define()
class Team(DiscordObject):
    icon: Optional[str] = attr.ib(default=None)
    members: List[TeamMember] = attr.ib(factory=list)
    name: str = attr.ib()
    owner_user_id: "Snowflake_Type" = attr.ib()

    # TODO: Lots of functions related to getting items
