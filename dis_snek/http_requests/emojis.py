from typing import TYPE_CHECKING, List

from dis_snek.const import MISSING
from dis_snek.models.route import Route

if TYPE_CHECKING:
    from dis_snek.http_client import HTTPClient
    from dis_snek.models.snowflake import Snowflake_Type


class EmojiRequests:
    request: "HTTPClient.request"

    async def get_all_guild_emoji(self, guild_id: "Snowflake_Type") -> List[dict]:
        """
        Get all the emoji from a guild.

        parameters:
            guild_id: The ID of the guild to query.

        Returns:
            List of emoji objects
        """
        return await self.request(Route("GET", f"/guilds/{guild_id}/emojis"))

    async def get_guild_emoji(self, guild_id: "Snowflake_Type", emoji_id: "Snowflake_Type") -> dict:
        """
        Get a specific guild emoji object

        parameters:
            guild_id: The ID of the guild to query
            emoji_id: The ID of the emoji to get

        Returns:
            Emoji object
        """
        data = await self.request(Route("GET", f"/guilds/{guild_id}/emojis/{emoji_id}"))
        if data:
            data["guild_id"] = guild_id
        return data

    async def create_guild_emoji(self, payload: dict, guild_id: "Snowflake_Type", reason: str = MISSING) -> dict:
        """
        Create a guild emoji.

        parameters:
            payload: The emoji's data
            guild_id: The ID of the guild
            reason: The reason for this creation

        Returns:
            The created emoji object
        """
        return await self.request(Route("POST", f"/guilds/{guild_id}/emojis"), data=payload, reason=reason)

    async def modify_guild_emoji(
        self, payload: dict, guild_id: "Snowflake_Type", emoji_id: "Snowflake_Type", reason: str = MISSING
    ) -> dict:
        """
        Modify an existing guild emoji.

        parameters:
            payload: The emoji's data
            guild_id: The ID of the guild
            emoji_id: The ID of the emoji to update
            reason: The reason for this creation

        Returns:
            The updated emoji object
        """
        return await self.request(Route("PATCH", f"/guilds/{guild_id}/emojis/{emoji_id}"), data=payload, reason=reason)

    async def delete_guild_emoji(
        self, guild_id: "Snowflake_Type", emoji_id: "Snowflake_Type", reason: str = MISSING
    ) -> None:
        """
        Delete a guild emoji.

        Args:
            guild_id: The ID of the guild
            emoji_id: The ID of the emoji to update
            reason: The reason for this deletion
        """
        await self.request(Route("DELETE", f"/guilds/{guild_id}/emojis/{emoji_id}"), reason=reason)
