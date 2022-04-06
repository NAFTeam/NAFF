from typing import TYPE_CHECKING, List, Any

import discord_typings

from dis_snek.client.const import MISSING, Absent
from ..route import Route

__all__ = ["EmojiRequests"]


if TYPE_CHECKING:
    from dis_snek.models.discord.snowflake import Snowflake_Type


class EmojiRequests:
    request: Any

    async def get_all_guild_emoji(self, guild_id: "Snowflake_Type") -> List[discord_typings.EmojiData]:
        """
        Get all the emoji from a guild.

        Args:
            guild_id: The ID of the guild to query.

        Returns:
            List of emoji objects

        """
        return await self.request(Route("GET", f"/guilds/{guild_id}/emojis"))

    async def get_guild_emoji(
        self, guild_id: "Snowflake_Type", emoji_id: "Snowflake_Type"
    ) -> discord_typings.EmojiData:
        """
        Get a specific guild emoji object.

        Args:
            guild_id: The ID of the guild to query
            emoji_id: The ID of the emoji to get

        Returns:
            PartialEmoji object

        """
        data = await self.request(Route("GET", f"/guilds/{guild_id}/emojis/{emoji_id}"))
        if data:
            data["guild_id"] = guild_id
        return data

    async def create_guild_emoji(
        self, payload: dict, guild_id: "Snowflake_Type", reason: Absent[str] = MISSING
    ) -> discord_typings.EmojiData:
        """
        Create a guild emoji.

        Args:
            payload: The emoji's data
            guild_id: The ID of the guild
            reason: The reason for this creation

        Returns:
            The created emoji object

        """
        return await self.request(Route("POST", f"/guilds/{guild_id}/emojis"), data=payload, reason=reason)

    async def modify_guild_emoji(
        self, payload: dict, guild_id: "Snowflake_Type", emoji_id: "Snowflake_Type", reason: Absent[str] = MISSING
    ) -> discord_typings.EmojiData:
        """
        Modify an existing guild emoji.

        Args:
            payload: The emoji's data
            guild_id: The ID of the guild
            emoji_id: The ID of the emoji to update
            reason: The reason for this creation

        Returns:
            The updated emoji object

        """
        return await self.request(Route("PATCH", f"/guilds/{guild_id}/emojis/{emoji_id}"), data=payload, reason=reason)

    async def delete_guild_emoji(
        self, guild_id: "Snowflake_Type", emoji_id: "Snowflake_Type", reason: Absent[str] = MISSING
    ) -> None:
        """
        Delete a guild emoji.

        Args:
            guild_id: The ID of the guild
            emoji_id: The ID of the emoji to update
            reason: The reason for this deletion

        """
        await self.request(Route("DELETE", f"/guilds/{guild_id}/emojis/{emoji_id}"), reason=reason)
