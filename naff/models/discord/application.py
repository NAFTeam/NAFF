from typing import TYPE_CHECKING, List, Optional, Dict, Any

from naff.client.const import MISSING
from naff.client.utils.attr_utils import define, field
from naff.client.utils.attr_converters import optional
from naff.models.discord.asset import Asset
from naff.models.discord.enums import ApplicationFlags
from naff.models.discord.snowflake import Snowflake_Type, to_snowflake
from naff.models.discord.team import Team
from .base import DiscordObject

if TYPE_CHECKING:
    from naff.client import Client
    from naff.models import User

__all__ = ("Application",)


@define()
class Application(DiscordObject):
    """Represents a discord application."""

    name: str = field(repr=True)
    """The name of the application"""
    icon: Optional[Asset] = field(default=None)
    """The icon of the application"""
    description: Optional[str] = field(default=None)
    """The description of the application"""
    rpc_origins: Optional[List[str]] = field(default=None)
    """An array of rpc origin urls, if rpc is enabled"""
    bot_public: bool = field(default=True)
    """When false only app owner can join the app's bot to guilds"""
    bot_require_code_grant: bool = field(default=False)
    """When true the app's bot will only join upon completion of the full oauth2 code grant flow"""
    terms_of_service_url: Optional[str] = field(default=None)
    """The url of the app's terms of service"""
    privacy_policy_url: Optional[str] = field(default=None)
    """The url of the app's privacy policy"""
    owner_id: Optional[Snowflake_Type] = field(default=None, converter=optional(to_snowflake))
    """The id of the owner of the application"""
    summary: str = field()
    """If this application is a game sold on Discord, this field will be the summary field for the store page of its primary sku"""
    verify_key: Optional[str] = field(default=MISSING)
    """The hex encoded key for verification in interactions and the GameSDK's GetTicket"""
    team: Optional["Team"] = field(default=None)
    """If the application belongs to a team, this will be a list of the members of that team"""
    guild_id: Optional["Snowflake_Type"] = field(default=None)
    """If this application is a game sold on Discord, this field will be the guild to which it has been linked"""
    primary_sku_id: Optional["Snowflake_Type"] = field(default=None)
    """If this application is a game sold on Discord, this field will be the id of the "Game SKU" that is created, if exists"""
    slug: Optional[str] = field(default=None)
    """If this application is a game sold on Discord, this field will be the URL slug that links to the store page"""
    cover_image: Optional[Asset] = field(default=None)
    """The application's default rich presence invite cover"""
    flags: Optional["ApplicationFlags"] = field(default=None, converter=optional(ApplicationFlags))
    """The application's public flags"""
    tags: Optional[List[str]] = field(default=None)
    """The application's tags describing its functionality and content"""
    # todo: implement an ApplicationInstallParams object. See https://discord.com/developers/docs/resources/application#install-params-object
    install_params: Optional[dict] = field(default=None)
    """The application's settings for in-app invitation to guilds"""
    custom_install_url: Optional[str] = field(default=None)
    """The application's custom authorization link for invitation to a guild"""

    @classmethod
    def _process_dict(cls, data: Dict[str, Any], client: "Client") -> Dict[str, Any]:
        if data.get("team"):
            data["team"] = Team.from_dict(data["team"], client)
            data["owner_id"] = data["team"].owner_user_id
        else:
            if "owner" in data:
                owner = client.cache.place_user_data(data.pop("owner"))
                data["owner_id"] = owner.id

        if data.get("icon"):
            data["icon"] = Asset.from_path_hash(client, f"app-icons/{data['id']}/{{}}", data["icon"])
        if data.get("cover_image"):
            data["cover_image"] = Asset.from_path_hash(client, f"app-icons/{data['id']}/{{}}", data["cover_image"])

        return data

    @property
    def owner(self) -> "User":
        """The user object for the owner of this application"""
        return self._client.cache.get_user(self.owner_id)
