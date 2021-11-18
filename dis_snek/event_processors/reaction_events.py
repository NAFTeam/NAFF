import logging

from dis_snek.const import logger_name
from dis_snek.event_processors._template import EventMixinTemplate
from dis_snek.models import listen, events, Emoji, Reaction
from dis_snek.models.events import RawGatewayEvent

log = logging.getLogger(logger_name)


class ReactionEvents(EventMixinTemplate):
    @listen()
    async def _on_raw_message_reaction_add(self, data: dict) -> None:
        add = event.override_name == "raw_message_reaction_add"

        if member := data.get("member"):
            author = self.cache.place_member_data(data.get("guild_id"), member)
        else:
            author = await self.cache.get_user(data.get("user_id"))

        emoji = Emoji.from_dict(data.get("emoji"))  # type: ignore
        message = await self.cache.get_message(data.get("channel_id"), data.get("message_id"), request_fallback=False)

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
                            "channel_id": message.channel.id,
                        },
                        self,  # type: ignore
                    )
                )

            self.cache.message_cache[(message.channel.id, message.id)] = message
        else:
            message = await self.cache.get_message(data.get("channel_id"), data.get("message_id"))

        if add:
            self.dispatch(events.MessageReactionAdd(message=message, emoji=emoji, author=author))
        else:
            self.dispatch(events.MessageReactionRemove(message=message, emoji=emoji, author=author))

    @listen()
    async def _on_raw_message_reaction_remove(self, data: dict) -> None:
        await self._on_raw_message_reaction_add(event)

    @listen()
    async def _on_raw_message_reaction_remove_all(self, data: dict) -> None:
        self.dispatch(
            events.MessageReactionRemoveAll(
                data.get("guild_id"),
                await self.cache.get_message(data["channel_id"], data["message_id"]),
            )
        )
