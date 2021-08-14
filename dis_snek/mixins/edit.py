from typing import Any, Dict, List, Optional, Union

from dis_snek.models.discord_objects.components import ActionRow, process_components
from dis_snek.models.discord_objects.embed import Embed


class EditMixin:
    def _edit_http_method(self) -> Any:
        pass

    async def edit(
        self,
        content: Optional[str],
        embeds: Optional[List[Embed]] = None,
        components: Optional[List[Union[Dict, ActionRow]]] = None,
    ):
        """
        Edit an existing message

        :param content: New content
        :param embeds: List of embeds, defaults to None
        :param components: [description], defaults to None
        :return: New message object
        """
        # TODO: InteractionContext handling
        if embeds is None:
            embeds = []
        embeds = [e.to_dict() for e in embeds]

        method = self._edit_http_method()

        components = process_components(components) if components else []
        await method(self.channel_id, self.id, content, embeds, components)
