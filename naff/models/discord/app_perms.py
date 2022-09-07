from typing import TYPE_CHECKING

from naff.client.utils import define, field
from naff.models.discord.base import DiscordObject, ClientObject
from naff.models.discord.enums import InteractionPermissionTypes
from naff.models.discord.snowflake import to_snowflake

if TYPE_CHECKING:
    from naff import Snowflake_Type, Guild

__all__ = ("ApplicationCommandPermission",)


@define()
class ApplicationCommandPermission(DiscordObject):
    id: "Snowflake_Type" = field(converter=to_snowflake)
    """ID of the role user or channel"""
    type: InteractionPermissionTypes = field(converter=InteractionPermissionTypes)
    """Type of permission (role user or channel)"""
    permission: bool = field(default=False)
    """Whether the command is enabled for this permission"""


@define()
class CommandPermissions(ClientObject):
    command_id: "Snowflake_Type" = field()
    _guild: "Guild" = field()

    permissions: dict["Snowflake_Type", ApplicationCommandPermission] = field(factory=dict, init=False)

    def is_enabled(self, *object_id) -> bool:
        """
        Check if a command is enabled for given scope(s). Takes into account the permissions for the bot itself

        Args:
            *object_id: The object(s) ID to check for.

        Returns:
            Whether the command is enabled for the given scope(s).
        """
        bot_perms = self._guild.command_permissions.get(self._client.app.id)

        for obj_id in object_id:
            if permission := self.permissions.get(obj_id):
                if not permission.permission:
                    return False

            if bot_perms:
                if permission := bot_perms.permissions.get(obj_id):
                    if not permission.permission:
                        return False
        return True

    def set_permission(self, permission: ApplicationCommandPermission) -> None:
        """
        Set a permission for the command.

        Args:
            permission: The permission to set.
        """
        self.permissions[permission.id] = permission
