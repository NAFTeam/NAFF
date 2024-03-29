from typing import TYPE_CHECKING, cast

import discord_typings

from naff.models.naff.protocols import CanRequest
from ..route import Route

__all__ = ("EmojiRequests",)


if TYPE_CHECKING:
    from naff.models.discord.snowflake import Snowflake_Type


class EmojiRequests(CanRequest):
    async def get_all_guild_emoji(self, guild_id: "Snowflake_Type") -> list[discord_typings.EmojiData]:
        """
        Get all the emoji from a guild.

        Args:
            guild_id: The ID of the guild to query.

        Returns:
            List of emoji objects

        """
        result = await self.request(Route("GET", f"/guilds/{int(guild_id)}/emojis"))
        return cast(list[discord_typings.EmojiData], result)

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
        result = await self.request(Route("GET", f"/guilds/{int(guild_id)}/emojis/{int(emoji_id)}"))
        return cast(discord_typings.EmojiData, result)

    async def create_guild_emoji(
        self, payload: dict, guild_id: "Snowflake_Type", reason: str | None = None
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
        result = await self.request(Route("POST", f"/guilds/{int(guild_id)}/emojis"), payload=payload, reason=reason)
        return cast(discord_typings.EmojiData, result)

    async def modify_guild_emoji(
        self, payload: dict, guild_id: "Snowflake_Type", emoji_id: "Snowflake_Type", reason: str | None = None
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
        result = await self.request(
            Route("PATCH", f"/guilds/{int(guild_id)}/emojis/{int(emoji_id)}"), payload=payload, reason=reason
        )
        return cast(discord_typings.EmojiData, result)

    async def delete_guild_emoji(
        self, guild_id: "Snowflake_Type", emoji_id: "Snowflake_Type", reason: str | None = None
    ) -> None:
        """
        Delete a guild emoji.

        Args:
            guild_id: The ID of the guild
            emoji_id: The ID of the emoji to update
            reason: The reason for this deletion

        """
        await self.request(Route("DELETE", f"/guilds/{int(guild_id)}/emojis/{int(emoji_id)}"), reason=reason)
