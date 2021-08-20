from typing import Any, Dict, List, Optional, Union

from dis_snek.models.discord_objects.components import BaseComponent, process_components
from dis_snek.models.discord_objects.embed import Embed


class EditMixin:
    def _edit_http_method(self) -> Any:
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
        # TODO: InteractionContext handling
        # Wrap single instances in a list
        if isinstance(embeds, (Embed, dict)):
            embeds = [embeds]
        # Handle none
        if embeds is None:
            embeds = []
        elif isinstance(embeds, list):
            embeds = [e.to_dict() if isinstance(e, Embed) else e for e in embeds]
        components = process_components(components) if components else []

        method = self._edit_http_method()

        await method(self.channel_id, self.id, content, embeds, components)
