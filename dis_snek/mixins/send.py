from typing import TYPE_CHECKING, Dict, List, Optional, Union

from aiohttp.formdata import FormData
from dis_snek.models.discord_objects.components import process_components
from dis_snek.models.discord_objects.embed import process_embeds
from dis_snek.models.enums import MessageFlags

if TYPE_CHECKING:
    from pathlib import Path

    from dis_snek.models.discord_objects.components import BaseComponent
    from dis_snek.models.discord_objects.embed import Embed
    from dis_snek.models.discord_objects.message import AllowedMentions, Message


class SendMixin:
    async def _send_http_request(self, message: Union[dict, FormData]) -> dict:
        raise NotImplementedError

    async def send(
        self,
        content: Optional[str] = None,
        embeds: Optional[Union[List[Union["Embed", Dict]], Union["Embed", Dict]]] = None,
        filepath: Union[str, "Path"] = None,
        components: Optional[
            Union[List[List[Union["BaseComponent", Dict]]], List[Union["BaseComponent", Dict]], "BaseComponent", Dict]
        ] = None,
        tts: Optional[bool] = False,
        allowed_mentions: Optional[Union["AllowedMentions", Dict]] = None,
        flags: Optional[Union[int, MessageFlags]] = None,
    ) -> "Message":
        """
        Send a message

        :param content: Message text content.
        :param embeds: Embeds to send, defaults to None.
        :param files: Files to send, defaults to None.
        :param components: Components to send, defaults to None.
        :param tts: Should this message use TTS.
        :param allowed_mentions: Allowed mentions.

        :return: New message object.
        """
        embeds = process_embeds(embeds)
        components = process_components(components)
        if allowed_mentions and not isinstance(allowed_mentions, dict):
            allowed_mentions = allowed_mentions.to_dict()

        message = dict(
            content=content,
            embeds=embeds,
            components=components,
            tts=tts,
            allowed_mentions=allowed_mentions,
            flags=flags,
        )

        # Remove keys without any data.
        message = {k: v for k, v in message.items() if v}

        message_data = None
        if filepath:
            # Some special checks when sending file.
            if embeds or allowed_mentions:
                raise ValueError("Embeds and allow mentions is not supported when sending a file.")
            if flags and flags & MessageFlags.EPHEMERAL == flags:
                raise ValueError("Ephemeral messages does not support sending of files.")

            # We need to use multipart/form-data for file sending here.
            form = FormData(message)
            with open(str(filepath), "rb") as buffer:
                form.add_field("file", buffer)
                message_data = await self._send_http_request(form)
        else:
            message_data = await self._send_http_request(message)

        if message_data:
            return self._client.cache.place_message_data(message_data)
