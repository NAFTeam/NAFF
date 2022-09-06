from typing import TYPE_CHECKING

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
        guild_id = event.data["guild_id"]
        cmd_id = event.data["id"]

        cmd = self.interactions.get(cmd_id)
        if cmd:
            # todo: set perms on cmd_object
            ...

        self.dispatch(events.ApplicationCommandPermissionsUpdate(guild_id, cmd_id, perms))
