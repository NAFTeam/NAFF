from typing import TYPE_CHECKING, Any, List, Optional

from dis_snek.const import MISSING
from dis_snek.models.route import Route

if TYPE_CHECKING:
    from aiohttp import FormData
    from dis_snek.models.snowflake import Snowflake_Type


class StickerRequests:
    request: Any

    async def get_sticker(self, sticker_id: "Snowflake_Type") -> dict:
        """
        Get a specific sticker.

        parameters:
            sticker_id: The id of the sticker
        returns:
            Sticker or None
        """
        return await self.request(Route("GET", f"/stickers/{sticker_id}"))

    async def list_nitro_sticker_packs(self) -> list:
        """
        Gets the list of sticker packs available to Nitro subscribers.

        returns:
            List of sticker packs
        """
        return await self.request(Route("GET", "/sticker-packs"))

    async def list_guild_stickers(self, guild_id: "Snowflake_Type") -> List[dict]:
        """
        Get the stickers for a guild.

        parameters:
            guild_id: The guild to get stickers from
        returns:
            List of Stickers or None
        """
        return await self.request(Route("GET", f"/guild/{guild_id}/stickers"))

    async def get_guild_sticker(self, guild_id: "Snowflake_Type", sticker_id: "Snowflake_Type") -> dict:
        """
        Get a sticker from a guild.

        parameters:
            guild_id: The guild to get stickers from
            sticker_id: The sticker to get from the guild
        returns:
            Sticker or None
        """
        return await self.request(Route("GET", f"/guild/{guild_id}/stickers/{sticker_id}"))

    async def create_guild_sticker(
        self, payload: "FormData", guild_id: "Snowflake_Type", reason: Optional[str] = MISSING
    ):
        """
        Create a new sticker for the guild. Requires the MANAGE_EMOJIS_AND_STICKERS permission.

        parameters:
            payload: the payload to send.
            guild_id: The guild to create sticker at.
            reason: The reason for this action.

        returns:
            The new sticker data on success.
        """
        return await self.request(Route("POST", f"/guild/{guild_id}/stickers"), data=payload, reason=reason)

    async def modify_guild_sticker(
        self, payload: dict, guild_id: "Snowflake_Type", sticker_id: "Snowflake_Type", reason: Optional[str] = MISSING
    ):
        """
        Modify the given sticker. Requires the MANAGE_EMOJIS_AND_STICKERS permission.

        parameters:
            payload: the payload to send.
            guild_id: The guild of the target sticker.
            sticker_id:  The sticker to modify.
            reason: The reason for this action.

        returns:
            The updated sticker data on success.
        """
        return await self.request(
            Route("PATCH", f"/guild/{guild_id}/stickers/{sticker_id}"), data=payload, reason=reason
        )

    async def delete_guild_sticker(
        self, guild_id: "Snowflake_Type", sticker_id: "Snowflake_Type", reason: Optional[str] = MISSING
    ) -> None:
        """
        Delete the given sticker. Requires the MANAGE_EMOJIS_AND_STICKERS permission.

        parameters:
            guild_id: The guild of the target sticker.
            sticker_id:  The sticker to delete.
            reason: The reason for this action.

        returns:
            Returns 204 No Content on success.
        """
        return await self.request(Route("DELETE", f"/guild/{guild_id}/stickers/{sticker_id}"), reason=reason)
