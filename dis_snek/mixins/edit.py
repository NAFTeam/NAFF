from typing import Any, Dict, List, Optional, Union

from dis_snek.models.discord_objects.components import BaseComponent, process_components
from dis_snek.models.discord_objects.embed import Embed, process_embeds


class EditMixin:
    def _edit_http_request(self) -> Any:
        pass

    async def edit(
        self,
        content: Optional[str],
        embeds: Optional[Union[List[Embed], Embed]] = None,
        components: Optional[
            Union[List[List[Union[BaseComponent, Dict]]], List[Union[BaseComponent, Dict]], BaseComponent, Dict]
        ] = None,
    ):
        """
        Edit an existing message

        :param content: New content
        :param embeds: List of embeds, defaults to None
        :param components: [description], defaults to None
        :return: New message object
        """
        # TODO: InteractionContext handling.
        # Ben: Do we really need edit in InteractionContext? Its just for the message itself, no?

        embeds = process_embeds(embeds)

        components = process_components(components)

        message = dict(
            content=content,
            embeds=embeds,
            components=components,
        )

        # Remove keys without any data.
        message = {k: v for k, v in message.items() if v}

        message_data = await self._edit_http_request(message)

        if message_data:
            return await self._client.cache.place_message_data(
                message_data["channel_id"], message_data["id"], message_data
            )
