from typing import TYPE_CHECKING, List, Optional, Dict, Any, Union

from naff.client.utils.attr_utils import define, field
from naff.models.discord.asset import Asset
from naff.models.discord.enums import TeamMembershipState
from naff.models.discord.snowflake import to_snowflake
from .base import DiscordObject

if TYPE_CHECKING:
    from naff.models.discord.user import User
    from naff.models.discord.snowflake import Snowflake_Type, SnowflakeObject
    from naff.client import Client

__all__ = ("TeamMember", "Team")


@define()
class TeamMember(DiscordObject):
    membership_state: TeamMembershipState = field(converter=TeamMembershipState)
    """Rhe user's membership state on the team"""
    # permissions: List[str] = field(default=["*"])  # disabled until discord adds more team roles
    team_id: "Snowflake_Type" = field(repr=True)
    """Rhe id of the parent team of which they are a member"""
    user: "User" = field()  # TODO: cache partial user (avatar, discrim, id, username)
    """Rhe avatar, discriminator, id, and username of the user"""

    @classmethod
    def _process_dict(cls, data: Dict[str, Any], client: "Client") -> Dict[str, Any]:
        data["user"] = client.cache.place_user_data(data["user"])
        data["id"] = data["user"].id
        return data


@define()
class Team(DiscordObject):
    icon: Optional[Asset] = field(default=None)
    """A hash of the image of the team's icon"""
    members: List[TeamMember] = field(factory=list)
    """The members of the team"""
    name: str = field(repr=True)
    """The name of the team"""
    owner_user_id: "Snowflake_Type" = field(converter=to_snowflake)
    """The user id of the current team owner"""

    @classmethod
    def _process_dict(cls, data: Dict[str, Any], client: "Client") -> Dict[str, Any]:
        data["members"] = TeamMember.from_list(data["members"], client)
        if data["icon"]:
            data["icon"] = Asset.from_path_hash(client, f"team-icons/{data['id']}/{{}}", data["icon"])
        return data

    @property
    def owner(self) -> "User":
        """The owner of the team"""
        return self._client.cache.get_user(self.owner_user_id)

    def is_in_team(self, user: Union["SnowflakeObject", "Snowflake_Type"]) -> bool:
        """
        Returns True if the passed user or ID is a member within the team.

        Args:
            user: The user or user ID to check

        Returns:
            Boolean indicating whether the user is in the team
        """
        return to_snowflake(user) in [m.id for m in self.members]
