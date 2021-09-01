from typing import TYPE_CHECKING, List

from dis_snek.models.route import Route

if TYPE_CHECKING:
    from dis_snek.http_client import HTTPClient
    from dis_snek.models.snowflake import Snowflake_Type


class EmojiRequests:
    request: "HTTPClient.request"

    async def list_guild_emojis(self, guild_id: "Snowflake_Type") -> List[dict]:
        """
        
        """
        return await self.request(Route("GET", f"/guilds/{guild_id}/emojis"))

    async def get_guild_emoji(self, guild_id: "Snowflake_Type", emoji_id: "Snowflake_Type") -> dict:
        """
        
        """
        return await self.request(Route("GET", f"/guilds/{guild_id}/emojis/{emoji_id}"))

    async def create_guild_emoji(self, payload: dict, guild_id: "Snowflake_Type") -> dict:
        """
        
        """
        return await self.request(Route("POST", f"/guilds/{guild_id}/emojis"), data=payload)

    async def modify_guild_emoji(self, payload: dict, guild_id: "Snowflake_Type", emoji_id: "Snowflake_Type") -> dict:
        """
        
        """
        return await self.request(Route("PATCH", f"/guilds/{guild_id}/emojis/{emoji_id}"), data=payload)

    async def delete_guild_emoji(self, guild_id: "Snowflake_Type", emoji_id: "Snowflake_Type") -> None:
        """
        
        """
        await self.request(Route("DELETE", f"/guilds/{guild_id}/emojis/{emoji_id}"))
