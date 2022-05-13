from typing import Any, List

import discord_typings

from ..route import Route

__all__ = ("BotRequests",)


class BotRequests:
    request: Any

    async def get_current_bot_information(self) -> discord_typings.ApplicationData:
        """
        Gets the bot's application object without flags.

        Returns:
            application object

        """
        return await self.request(Route("GET", "/oauth2/applications/@me"))

    async def get_current_authorisation_information(self) -> dict:
        """
        Gets info about the current authorization.

        Returns:
            Authorisation information

        """
        return await self.request(Route("GET", "/oauth2/@me"))

    async def list_voice_regions(self) -> List[discord_typings.VoiceRegionData]:
        """
        Gets an array of voice region objects that can be used when setting a voice or stage channel's `rtc_region`.

        Returns:
            an array of voice region objects

        """
        return await self.request(Route("GET", "/voice/regions"))
