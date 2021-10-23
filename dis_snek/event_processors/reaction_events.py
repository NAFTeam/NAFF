import copy
import logging

from dis_snek.const import logger_name, MISSING
from dis_snek.event_processors._template import EventMixinTemplate
from dis_snek.models import listen, events, Emoji, CustomEmoji
from dis_snek.models.events import RawGatewayEvent

log = logging.getLogger(logger_name)


class ReactionEvents(EventMixinTemplate):
    @listen()
    async def _on_raw_message_reaction_add(self, event: RawGatewayEvent) -> None:
        if member := event.data.get("member"):
            author = self.cache.place_member_data(event.data.get("guild_id"), member)
        else:
            author = await self.cache.get_user(event.data.get("user_id"))

        if event.data["emoji"].get("id") is not None:
            emoji = CustomEmoji.from_dict(event.data.get("emoji"), self)  # type: ignore
        else:
            emoji = Emoji.from_dict(event.data.get("emoji"), self)  # type: ignore

        message = await self.cache.get_message(
            event.data.get("channel_id"), event.data.get("message_id")
        ) or event.data.get("message_id")
        if event.override_name == "raw_message_reaction_add":
            self.dispatch(events.MessageReactionAdd(message=message, emoji=emoji, author=author))
        else:
            self.dispatch(events.MessageReactionRemove(message=message, emoji=emoji, author=author))

    @listen()
    async def _on_raw_message_reaction_remove(self, event: RawGatewayEvent) -> None:
        await self._on_raw_message_reaction_add(event)

    @listen()
    async def _on_raw_message_reaction_remove_all(self, event: RawGatewayEvent) -> None:
        self.dispatch(
            events.MessageReactionRemoveAll(
                event.data.get("guild_id"),
                await self.cache.get_message(event.data["channel_id"], event.data["message_id"]),
            )
        )
