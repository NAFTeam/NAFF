import logging
from typing import TYPE_CHECKING

import dis_snek.api.events as events

from dis_snek.client.const import logger_name
from ._template import EventMixinTemplate, Processor
from dis_snek.models import PartialEmoji, Reaction

if TYPE_CHECKING:
    from dis_snek.api.events import RawGatewayEvent

__all__ = ["ReactionEvents"]

log = logging.getLogger(logger_name)


class ReactionEvents(EventMixinTemplate):
    @Processor.define()
    async def _on_raw_message_reaction_add(self, event: "RawGatewayEvent") -> None:
        add = event.override_name == "raw_message_reaction_add"

        if member := event.data.get("member"):
            author = self.cache.place_member_data(event.data.get("guild_id"), member)
        else:
            author = await self.cache.fetch_user(event.data.get("user_id"))

        emoji = PartialEmoji.from_dict(event.data.get("emoji"))  # type: ignore
        message = await self.cache.fetch_message(
            event.data.get("channel_id"), event.data.get("message_id"), request_fallback=False
        )

        if message:
            for i in range(len(message.reactions)):
                r = message.reactions[i]
                if r.emoji == emoji:
                    if add:
                        r.count += 1
                    else:
                        r.count -= 1

                    if r.count <= 0:
                        message.reactions.pop(i)
                    else:
                        message.reactions[i] = r
                    break
            else:
                message.reactions.append(
                    Reaction.from_dict(
                        {
                            "count": 1,
                            "me": author.id == self.user.id,  # type: ignore
                            "emoji": emoji.to_dict(),
                            "message_id": message.id,
                            "channel_id": message._channel_id,
                        },
                        self,  # type: ignore
                    )
                )

            self.cache.message_cache[(message._channel_id, message.id)] = message
        else:
            message = await self.cache.fetch_message(event.data.get("channel_id"), event.data.get("message_id"))

        if add:
            self.dispatch(events.MessageReactionAdd(message=message, emoji=emoji, author=author))
        else:
            self.dispatch(events.MessageReactionRemove(message=message, emoji=emoji, author=author))

    @Processor.define()
    async def _on_raw_message_reaction_remove(self, event: "RawGatewayEvent") -> None:
        await self._on_raw_message_reaction_add.callback(self, event)

    @Processor.define()
    async def _on_raw_message_reaction_remove_all(self, event: "RawGatewayEvent") -> None:
        self.dispatch(
            events.MessageReactionRemoveAll(
                event.data.get("guild_id"),
                await self.cache.fetch_message(event.data["channel_id"], event.data["message_id"]),
            )
        )
