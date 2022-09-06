from typing import TYPE_CHECKING

from naff.client.utils import define, field
from naff.models.discord.base import DiscordObject
from naff.models.discord.enums import InteractionPermissionTypes
from naff.models.discord.snowflake import to_snowflake

if TYPE_CHECKING:
    from naff import Snowflake_Type

__all__ = ("ApplicationCommandPermission",)


@define()
class ApplicationCommandPermission(DiscordObject):
    id: "Snowflake_Type" = field(converter=to_snowflake)
    """ID of the role user or channel"""
    type: InteractionPermissionTypes = field(converter=InteractionPermissionTypes)
    """Type of permission (role user or channel)"""
    permission: bool = field(default=False)
    """Whether the command is enabled for this permission"""
