from typing import TYPE_CHECKING, List, Optional, Dict, Any, Union

import attr

from dis_snek.models.discord_objects.asset import Asset
from dis_snek.models.discord import DiscordObject, ClientObject
from dis_snek.models.enums import TeamMembershipState
from dis_snek.models.snowflake import to_snowflake
from dis_snek.utils.attr_utils import define

if TYPE_CHECKING:
    from dis_snek.models.discord_objects.user import User
    from dis_snek.models.snowflake import Snowflake_Type, SnowflakeObject
    from dis_snek.client import Snake


@define()
class TeamMember(DiscordObject):
    membership_state: TeamMembershipState = attr.ib(converter=TeamMembershipState)
    # permissions: List[str] = attr.ib(default=["*"])  # disabled until discord adds more team roles
    team_id: "Snowflake_Type" = attr.ib()
    user: "User" = attr.ib()  # TODO: cache partial user (avatar, discrim, id, username)

    @classmethod
    def _process_dict(cls, data: Dict[str, Any], client: "Snake") -> Dict[str, Any]:
        data["user"] = client.cache.place_user_data(data["user"])
        data["id"] = data["user"].id
        return data


@define()
class Team(DiscordObject):
    icon: Optional[Asset] = attr.ib(default=None)
    members: List[TeamMember] = attr.ib(factory=list)
    name: str = attr.ib()
    owner_user_id: "Snowflake_Type" = attr.ib(converter=to_snowflake)

    @classmethod
    def _process_dict(cls, data: Dict[str, Any], client: "Snake") -> Dict[str, Any]:
        data["members"] = [TeamMember.from_dict(member, client) for member in data["members"]]
        if data["icon"]:
            data["icon"] = Asset.from_path_hash(client, f"team-icons/{data['id']}/{{}}.png", data["icon"])
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
