from typing import TYPE_CHECKING, List, Optional, Union

import dis_snek.client.errors as errors
import dis_snek.models as models

if TYPE_CHECKING:
    from io import IOBase
    from pathlib import Path

    from aiohttp.formdata import FormData

    from dis_snek.client import Snake
    from dis_snek.models import File
    from dis_snek.models.discord.components import BaseComponent
    from dis_snek.models.discord.embed import Embed
    from dis_snek.models.discord.message import AllowedMentions, Message, MessageReference
    from dis_snek.models.discord.sticker import Sticker
    from dis_snek.models.discord.snowflake import Snowflake_Type
    from dis_snek.models.discord.enums import MessageFlags

__all__ = ["SendMixin"]


class SendMixin:
    _client: "Snake"

    async def _send_http_request(self, message_payload: Union[dict, "FormData"]) -> dict:
        raise NotImplementedError

    async def send(
        self,
        content: Optional[str] = None,
        embeds: Optional[Union[List[Union["Embed", dict]], Union["Embed", dict]]] = None,
        embed: Optional[Union["Embed", dict]] = None,
        components: Optional[
            Union[List[List[Union["BaseComponent", dict]]], List[Union["BaseComponent", dict]], "BaseComponent", dict]
        ] = None,
        stickers: Optional[Union[List[Union["Sticker", "Snowflake_Type"]], "Sticker", "Snowflake_Type"]] = None,
        allowed_mentions: Optional[Union["AllowedMentions", dict]] = None,
        reply_to: Optional[Union["MessageReference", "Message", dict, "Snowflake_Type"]] = None,
        file: Optional[Union["File", "IOBase", "Path", str]] = None,
        tts: bool = False,
        flags: Optional[Union[int, "MessageFlags"]] = None,
        **kwargs,
    ) -> "Message":
        """
        Send a message.

        parameters:
            content: Message text content.
            embeds: Embedded rich content (up to 6000 characters).
            embed: Embedded rich content (up to 6000 characters).
            components: The components to include with the message.
            stickers: IDs of up to 3 stickers in the server to send in the message.
            allowed_mentions: Allowed mentions for the message.
            reply_to: Message to reference, must be from the same channel.
            file: Location of file to send, the bytes or the File() instance, defaults to None.
            tts: Should this message use Text To Speech.
            flags: Message flags to apply.

        returns:
            New message object that was sent.

        """
        if not content and not (embeds or embed) and not file:
            raise errors.EmptyMessageException("You cannot send a message without any content or embeds")
        message_payload = models.discord.message.process_message_payload(
            content=content,
            embeds=embeds or embed,
            components=components,
            stickers=stickers,
            allowed_mentions=allowed_mentions,
            reply_to=reply_to,
            file=file,
            tts=tts,
            flags=flags,
        )
        if kwargs:
            for key, value in kwargs.items():
                message_payload[key] = value

        message_data = await self._send_http_request(message_payload)
        if message_data:
            return self._client.cache.place_message_data(message_data)
