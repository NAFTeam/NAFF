from typing import Any

from dis_snek.models.route import Route
from dis_snek.models.snowflake import Snowflake_Type


class ReactionRequests:
    request: Any

    async def create_reaction(self, channel_id: Snowflake_Type, message_id: Snowflake_Type, emoji: str) -> None:
        """
        Create a reaction for a message.

        :param channel_id: The channel this is taking place in
        :param message_id: The message to create a a reaction on
        :param emoji: The emoji to use (format: `name:id`)
        """
        return await self.request(
            Route(
                "PUT",
                "/channels/{channel_id}/messages/{message_id}/reactions/{emoji}/@me",
                channel_id=channel_id,
                message_id=message_id,
                emoji=emoji,
            )
        )
