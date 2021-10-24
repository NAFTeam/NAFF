import copy
import logging

from dis_snek.const import logger_name, MISSING
from dis_snek.event_processors._template import EventMixinTemplate
from dis_snek.models import listen, events, Emoji, CustomEmoji, Reaction, Message
from dis_snek.models.events import RawGatewayEvent

log = logging.getLogger(logger_name)


class ReactionEvents(EventMixinTemplate):
    @listen()
    async def _on_raw_message_reaction_add(self, event: RawGatewayEvent) -> None:
        if member := event.data.get("member"):
            author = self.cache.place_member_data(event.data.get("guild_id"), member)
        else:
            author = await self.cache.get_user(event.data.get("user_id"))

        add = event.override_name == "raw_message_reaction_add"

        if event.data["emoji"].get("id") is not None:
            emoji = CustomEmoji.from_dict(event.data.get("emoji"), self)  # type: ignore
        else:
            emoji = Emoji.from_dict(event.data.get("emoji"))  # type: ignore

        message = await self.cache.get_message(
            event.data.get("channel_id"), event.data.get("message_id"), request_fallback=False
        )

        if message:
            # this is hacky but it will do until reaction.py is done
            # this also doesnt properly handle custom emoji
            for r in message.reactions:
                if r.emoji == event.data.get("emoji"):
                    if add:
                        r.count += 1
                    else:
                        r.count -= 1
                    break
            else:
                message.reactions.append(
                    Reaction.from_dict({"count": 1, "me": author.id == self.user.id, "emoji": emoji.to_dict()}, self)
                )
            self.cache.message_cache[message.id] = message
        else:
            message = await self.cache.get_message(event.data.get("channel_id"), event.data.get("message_id"))

        if add:
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
