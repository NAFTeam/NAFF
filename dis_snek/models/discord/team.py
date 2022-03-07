from typing import TYPE_CHECKING, List, Optional, Dict, Any, Union

from dis_snek.client.utils.attr_utils import define, field
from dis_snek.models.discord.asset import Asset
from dis_snek.models.discord.enums import TeamMembershipState
from dis_snek.models.discord.snowflake import to_snowflake
from .base import DiscordObject

if TYPE_CHECKING:
    from dis_snek.models.discord.user import User
    from dis_snek.models.discord.snowflake import Snowflake_Type, SnowflakeObject
    from dis_snek.client import Snake

__all__ = ["TeamMember", "Team"]


@define()
class TeamMember(DiscordObject):
    membership_state: TeamMembershipState = field(converter=TeamMembershipState)
    # permissions: List[str] = field(default=["*"])  # disabled until discord adds more team roles
    team_id: "Snowflake_Type" = field(repr=True)
    user: "User" = field()  # TODO: cache partial user (avatar, discrim, id, username)

    @classmethod
    def _process_dict(cls, data: Dict[str, Any], client: "Snake") -> Dict[str, Any]:
        data["user"] = client.cache.place_user_data(data["user"])
        data["id"] = data["user"].id
        return data


@define()
class Team(DiscordObject):
    icon: Optional[Asset] = field(default=None)
    members: List[TeamMember] = field(factory=list)
    name: str = field(repr=True)
    owner_user_id: "Snowflake_Type" = field(converter=to_snowflake)

    @classmethod
    def _process_dict(cls, data: Dict[str, Any], client: "Snake") -> Dict[str, Any]:
        data["members"] = TeamMember.from_list(data["members"], client)
        if data["icon"]:
            data["icon"] = Asset.from_path_hash(client, f"team-icons/{data['id']}/{{}}", data["icon"])
        return data

    @property
    def owner(self) -> "User":
        return self._client.cache.user_cache.get(self.owner_user_id)

    def is_in_team(self, user: Union["SnowflakeObject", "Snowflake_Type"]) -> bool:
        """
        Returns True if the passed user or ID is a member within the team.

        Args:
            user: The user or user ID to check

        Returns:
            Boolean indicating whether the user is in the team
        """
        return to_snowflake(user) in [m.id for m in self.members]
