from typing import TYPE_CHECKING, List, Optional

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

    async def create_guild_emoji(self, payload: dict, guild_id: "Snowflake_Type", reason: Optional[str] = None) -> dict:
        """
        
        """
        return await self.request(Route("POST", f"/guilds/{guild_id}/emojis"), data=payload, reason=reason)

    async def modify_guild_emoji(self, payload: dict, guild_id: "Snowflake_Type", emoji_id: "Snowflake_Type", reason: Optional[str] = None) -> dict:
        """
        
        """
        return await self.request(Route("PATCH", f"/guilds/{guild_id}/emojis/{emoji_id}"), data=payload, reason=reason)

    async def delete_guild_emoji(self, guild_id: "Snowflake_Type", emoji_id: "Snowflake_Type", reason: Optional[str] = None) -> None:
        """
        
        """
        await self.request(Route("DELETE", f"/guilds/{guild_id}/emojis/{emoji_id}"), reason=reason)
