from typing import Any, Dict, List, Optional, Union

from dis_snek.models.route import Route
from dis_snek.models.snowflake import Snowflake_Type


class StickerRequests:
    request: Any

    async def get_sticker(self, sticker_id: Snowflake_Type) -> dict:
        """
        Get a specific sticker.

        :param sticker_id: The id of the sticker
        :return: Sticker or None
        """
        return await self.request(Route("GET", f"/stickers/{sticker_id}"))

    async def get_guild_sticker(self, guild_id: Snowflake_Type, sticker_id: Snowflake_Type) -> dict:
        """
        Get a sticker from a guild.

        :param guild_id: The guild to get stickers from
        :param sticker_id: The sticker to get from the guild
        :return: Sticker or None
        """
        return await self.request(Route("GET", f"/guild/{guild_id}/stickers/{sticker_id}"))

    async def get_guild_stickers(self, guild_id: Snowflake_Type) -> List[dict]:
        """
        Get the stickers for a guild.

        :param guild_id: The guild to get stickers from
        :return: List of Stickers or None
        """
        return await self.request(Route("GET", f"/guild/{guild_id}/stickers"))
