from dis_snek.models.enums import MessageFlags
from pathlib import Path
from typing import TYPE_CHECKING, Any, Dict, List, Optional, Union

from aiohttp.formdata import FormData
from dis_snek.models.discord_objects.components import BaseComponent, process_components
from dis_snek.models.discord_objects.embed import Embed, process_embeds

if TYPE_CHECKING:
    from dis_snek.models.discord_objects.message import Message, AllowedMentions, Attachment


class EditMixin:
    async def _edit_http_request(self) -> Any:
        raise NotImplementedError

    async def edit(
        self,
        content: Optional[str] = None,
        embeds: Optional[Union[List[Union[Embed, Dict]], Union[Embed, Dict]]] = None,
        filepath: Union[str, Path] = None,
        components: Optional[
            Union[List[List[Union[BaseComponent, Dict]]], List[Union[BaseComponent, Dict]], BaseComponent, Dict]
        ] = None,
        tts: Optional[bool] = False,
        allowed_mentions: Optional[Union["AllowedMentions", Dict]] = None,
        flags: Optional[Union[int, MessageFlags]] = None,
        attachments: Optional[Union["Attachment", Dict]] = None,
    ) -> "Message":
        """
        Edit an existing message.

        :param content: Message text content.
        :param embeds: Embeds to send, defaults to None.
        :param files: Files to send, defaults to None.
        :param components: Components to send, defaults to None.
        :param tts: Should this message use TTS.
        :param allowed_mentions: Allowed mentions.
        :param attachments:

        :return: New message object.
        """
        # TODO: InteractionContext handling.
        # Ben: Do we really need edit in InteractionContext? Its just for the message itself, no?

        embeds = process_embeds(embeds)
        components = process_components(components)
        if allowed_mentions and not isinstance(allowed_mentions, dict):
            allowed_mentions = allowed_mentions.to_dict()

        # TODO Process attachments.

        message = dict(
            content=content,
            embeds=embeds,
            components=components,
            tts=tts,
            allowed_mentions=allowed_mentions,
            flags=flags,
            attachments=attachments,
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
                message_data = await self._edit_http_request(form)
        else:
            message_data = await self._edit_http_request(message)

        if message_data:
            return self._client.cache.place_message_data(message_data)
