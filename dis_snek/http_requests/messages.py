from typing import Optional, List, Dict

from mypy.build import Any

from dis_snek.models.route import Route
from dis_snek.models.snowflake import Snowflake_Type


class MessageRequests:
    request: Any

    async def create_message(
        self,
        channel_id: Snowflake_Type,
        content: Optional[str],
        tts: Optional[bool] = False,
        embeds: Optional[List[Dict]] = None,
        components: Optional[List[dict]] = None,
    ) -> Any:
        """Send a message to the specified channel. Incomplete."""
        # todo: Complete this
        payload: Dict[str, Any] = {}

        if content:
            payload["content"] = content
        if tts:
            payload["tts"] = tts
        if embeds:
            payload["embeds"] = embeds
        if components:
            payload["components"] = components
        return await self.request(Route("POST", f"/channels/{channel_id}/messages"), json=payload)
