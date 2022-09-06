from typing import TYPE_CHECKING

from naff.models.discord.snowflake import to_snowflake
from naff.models.discord.app_perms import ApplicationCommandPermission
from ._template import EventMixinTemplate, Processor
from ... import events

if TYPE_CHECKING:
    from naff.api.events import RawGatewayEvent

__all__ = ("IntegrationEvents",)


class IntegrationEvents(EventMixinTemplate):
    @Processor.define()
    async def _raw_application_command_permissions_update(self, event: "RawGatewayEvent") -> None:
        perms = [ApplicationCommandPermission.from_dict(perm, self) for perm in event.data["permissions"]]
        guild_id = to_snowflake(event.data["guild_id"])
        cmd_id = to_snowflake(event.data["id"])

        if self.app.id == cmd_id:
            # entire bot disabled in this guild
            ...  # todo: cache this
        else:
            # specific command disabled in this guild
            cmd = self.get_application_cmd_by_id(cmd_id)

            if cmd:
                cmd.permissions |= {perm.id: perm for perm in perms}

        self.dispatch(events.ApplicationCommandPermissionsUpdate(guild_id, cmd_id, perms))
