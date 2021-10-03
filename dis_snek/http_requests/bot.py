from typing import Any, List

from dis_snek.models.route import Route


class BotRequests:
    request: Any

    async def get_current_bot_information(self) -> dict:
        """
        Returns the bot's application object without flags.

        returns:
            application object
        """
        return await self.request(Route("GET", "/oauth2/applications/@me"))

    async def get_current_authorisation_information(self) -> dict:
        """
        Returns info about the current authorization

        returns:
            Authorisation information
        """
        return await self.request(Route("GET", "/oauth2/@me"))

    async def list_voice_regions(self) -> List[dict]:
        """
        Returns an array of voice region objects that can be used when setting a voice or stage channel's `rtc_region`.

        returns:
            an array of voice region objects
        """
        return await self.request(Route("GET", "/voice/regions"))
