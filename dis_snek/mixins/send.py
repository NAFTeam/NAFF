from typing import Any, Dict, List, Optional, Union

from dis_snek.models.discord_objects.components import BaseComponent, process_components
from dis_snek.models.discord_objects.embed import Embed


class SendMixin:
    def _send_http_method(self) -> Any:
        pass

    async def send(
        self,
        content: Optional[str],
        embeds: Optional[Union[List[Union[Embed, Dict]], Union[Embed, Dict]]] = None,
        components: Optional[
            List[List[Union[BaseComponent, Dict]], List[Union[BaseComponent, Dict]], BaseComponent, Dict]
        ] = None,
        tts: Optional[bool] = False,
        allowed_mentions: Optional[dict] = None,
    ):
        """Send a message

        :param content: Message content
        :param embeds: Embeds to send, defaults to None
        :param components: Components to send, defaults to None
        :param tts: Should this message use TTS
        :param allowed_mentions: Allowed mentions
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

        method = self._send_http_method()

        msg = await method(self.id, content, tts, embeds, components)
        return await self._client.cache.place_message_data(self.id, msg["id"], msg)
