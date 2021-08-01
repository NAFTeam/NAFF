"""
The MIT License (MIT).

Copyright (c) 2021 - present LordOfPolls

Permission is hereby granted, free of charge, to any person obtaining a
copy of this software and associated documentation files (the "Software"),
to deal in the Software without restriction, including without limitation
the rights to use, copy, modify, merge, publish, distribute, sublicense,
and/or sell copies of the Software, and to permit persons to whom the
Software is furnished to do so, subject to the following conditions:
The above copyright notice and this permission notice shall be included in
all copies or substantial portions of the Software.
THE SOFTWARE IS PROVIDED "AS IS", WITHOUT WARRANTY OF ANY KIND, EXPRESS
OR IMPLIED, INCLUDING BUT NOT LIMITED TO THE WARRANTIES OF MERCHANTABILITY,
FITNESS FOR A PARTICULAR PURPOSE AND NONINFRINGEMENT. IN NO EVENT SHALL THE
AUTHORS OR COPYRIGHT HOLDERS BE LIABLE FOR ANY CLAIM, DAMAGES OR OTHER
LIABILITY, WHETHER IN AN ACTION OF CONTRACT, TORT OR OTHERWISE, ARISING
FROM, OUT OF OR IN CONNECTION WITH THE SOFTWARE OR THE USE OR OTHER
DEALINGS IN THE SOFTWARE.
"""
import asyncio
import datetime
import logging
import traceback
from types import TracebackType
from typing import Any
from typing import Coroutine
from typing import Dict
from typing import List
from typing import Optional
from typing import Type
from typing import TypeVar
from typing import Union
from urllib.parse import quote as _uriquote

import aiohttp  # type: ignore
import orjson
from aiohttp import ClientWebSocketResponse
from multidict import CIMultiDictProxy  # type: ignore

from dis_snek.const import __py_version__
from dis_snek.const import __repo_url__
from dis_snek.const import __version__
from dis_snek.const import logger_name
from dis_snek.errors import DiscordError
from dis_snek.errors import Forbidden
from dis_snek.errors import GatewayNotFound
from dis_snek.errors import HTTPError
from dis_snek.errors import NotFound
from dis_snek.models.route import Route
from dis_snek.models.snowflake import Snowflake_Type
from dis_snek.utils.utils_json import response_decode

log = logging.getLogger(logger_name)

T = TypeVar("T")
BE = TypeVar("BE", bound=BaseException)
MU = TypeVar("MU", bound="CanUnlock")
Response = Coroutine[Any, Any, T]


class DiscordClientWebSocketResponse(aiohttp.ClientWebSocketResponse):
    """Represents the websocket connection with discord."""

    async def close(self, *, code: int = 4000, message: bytes = b"") -> bool:
        """
        Close the connection.

        :param code: The close code to use
        :param message: A message to send within the close
        """
        return await super().close(code=code, message=message)


class CanUnlock:
    """
    Handles locking and unlocking the event loop during requests.

    :param lock: An asyncio lock
    """

    def __init__(self, lock: asyncio.Lock) -> None:
        self.lock: asyncio.Lock = lock
        self._unlock: bool = True

    def __enter__(self: MU) -> MU:
        return self

    def defer(self) -> None:
        """Keep the lock active to allow for retries while a ratelimit pends."""
        self._unlock = False

    def __exit__(
        self,
        exc_type: Optional[Type[BE]],
        exc: Optional[BE],
        traceback: Optional[TracebackType],
    ) -> None:
        if self._unlock:
            self.lock.release()


class HTTPClient:
    """A http client for sending requests to the Discord API."""

    def __init__(
        self, connector: Optional[aiohttp.BaseConnector] = None, loop: Optional[asyncio.AbstractEventLoop] = None
    ):
        self.connector: Optional[aiohttp.BaseConnector] = connector
        self.loop = asyncio.get_event_loop() if loop is None else loop
        self.__session: aiohttp.ClientSession = aiohttp.ClientSession()
        self._retries: int = 5
        self.token: Optional[str] = None
        self.ratelimit_locks: Dict[str, asyncio.Lock] = {}

        self.user_agent: str = (
            f"DiscordBot ({__repo_url__} {__version__} Python/{__py_version__}) aiohttp/{aiohttp.__version__}"
        )

    def __del__(self):
        if self.__session and not self.__session.closed:
            self.loop.run_until_complete(self.__session.close())

    def _parse_ratelimit(self, header: CIMultiDictProxy[str]) -> dict:
        """
        Parse the ratelimit data into a more usable format.

        :param header: the header of the response
        :return:
        """
        return {
            "bucket": header.get("x-ratelimit-bucket"),
            "limit": header.get("x-ratelimit-limit"),
            "remaining": header.get("x-ratelimit-remaining"),
            "delta": float(header.get("x-ratelimit-reset-after")),  # type: ignore
            "time": datetime.datetime.utcfromtimestamp(float(header.get("x-ratelimit-reset"))),  # type: ignore
        }

    async def request(self, route: Route, **kwargs: Any) -> Any:
        """
        Make a request to the discord API.

        :param route: the route to use
        """
        headers: Dict[str, str] = {"User-Agent": self.user_agent}

        lock = self.ratelimit_locks.get(route.rl_bucket)
        if lock is None:
            lock = asyncio.Lock()
            if route.rl_bucket is not None:
                self.ratelimit_locks[route.rl_bucket] = lock

        if self.token is not None:
            headers["Authorization"] = "Bot " + self.token

        if "json" in kwargs:
            headers["Content-Type"] = "application/json"
            kwargs["data"] = orjson.dumps(kwargs.pop("json")).decode("utf-8")

        if "reason" in kwargs:
            headers["X-Audit-Log-Reason"] = _uriquote(kwargs.pop("reason"), safe="/ ")

        kwargs["headers"] = headers

        response: Optional[aiohttp.ClientResponse] = None
        data: Optional[Union[Dict[str, Any], str]] = None
        await lock.acquire()
        with CanUnlock(lock) as can_unlock:
            for tries in range(self._retries):
                try:
                    async with self.__session.request(route.method, route.url, **kwargs) as response:
                        log.debug(f"{route.method} {route.url} with {kwargs.get('data')} returned {response.status}")

                        data = await response_decode(response)

                        # ratelimits
                        remaining = response.headers.get("X-Ratelimit-Remaining")
                        if remaining == "0" and response.status != 429:
                            r_limit = self._parse_ratelimit(response.headers)
                            log.debug(
                                f"A rate limit has been reached. (Bucket: {route.rl_bucket} | "
                                f"Retrying in: {r_limit['delta']}"
                            )

                            can_unlock.defer()
                            self.loop.call_later(r_limit["delta"], lock.release)

                        if 300 > response.status >= 200:
                            log.debug(f"{route.method} {route.url} has received {data}")
                            return data

                        if response.status in {500, 502, 504}:
                            await asyncio.sleep(1 + tries * 2)
                            continue

                        if response.status == 403:
                            raise Forbidden(response.reason, route, response.status, response)
                        elif response.status == 404:
                            raise NotFound(response.reason, route, response.status, response)
                        elif response.status >= 500:
                            raise DiscordError(response.reason, route, response.status, response)
                        else:
                            raise HTTPError(response.reason, route, response.status, response)

                except OSError as e:
                    if tries < self._retries - 1 and e.errno in (54, 10054):
                        await asyncio.sleep(1 + tries * 2)
                        continue
                    raise
                except Exception as e:
                    log.error("".join(traceback.format_exception(type(e), e, e.__traceback__)))

    async def login(self, token: str) -> dict:
        """
        "Login" to the gateway, basically validates the token and grabs user data.

        :param token: the token to use
        :return: The currently logged in bot's data
        """
        self.__session = aiohttp.ClientSession(
            connector=self.connector, ws_response_class=DiscordClientWebSocketResponse
        )
        self.token = token
        try:
            return await self.request(Route("GET", "/users/@me"))
        except HTTPError as e:
            if e.status_code == 401:
                raise HTTPError("An improper token was passed", e.route, e.status_code, e.response) from e
            raise

    async def close(self) -> None:
        """Close the session."""
        if self.__session:
            await self.__session.close()

    async def logout(self) -> None:
        """Logout of the session."""
        await self.request(Route("POST", "/auth/logout"))

    async def get_gateway(self) -> str:
        """Get the gateway url."""
        try:
            data: dict = await self.request(Route("GET", "/gateway"))
        except HTTPError as exc:
            raise GatewayNotFound from exc
        return "{0}?encoding={1}&v=9&compress=zlib-stream".format(data["url"], "json")

    async def websock_connect(self, url: str) -> ClientWebSocketResponse:
        """
        Connect to the websocket.

        :param url: the url to connect to
        """
        return await self.__session.ws_connect(
            url, timeout=30, max_msg_size=0, autoclose=False, headers={"User-Agent": self.user_agent}, compress=0
        )

    # region getters

    async def get_user(self, user_id: Snowflake_Type) -> dict:
        """
        Get a user object for a given user ID.

        :param user_id: The user to get
        :return: user
        """
        return await self.request(Route("GET", f"/users/{user_id}"))

    async def get_message(self, channel_id: Snowflake_Type, message_id: Snowflake_Type) -> dict:
        """
        Get a specific message in the channel. Returns a message object on success.

        :param channel_id: the channel this message belongs to
        :param message_id: the id of the message
        :return: message or None
        """
        return await self.request(Route("GET", f"/channels/{channel_id}/messages/{message_id}"))

    async def get_channel(self, channel_id: Snowflake_Type) -> dict:
        """
        Get a channel by ID. Returns a channel object. If the channel is a thread, a thread member object is included.

        :param channel_id: The id of the channel
        :return: channel
        """
        return await self.request(Route("GET", f"/channels/{channel_id}"))

    async def get_guilds(
        self, limit: int = 200, before: Optional[Snowflake_Type] = None, after: Optional[Snowflake_Type] = None
    ) -> List[Dict]:
        """
        Get a list of partial guild objects the current user is a member of req. `guilds` scope.

        :param limit: max number of guilds to return (1-200)
        :param before: get guilds before this guild ID
        :param after: get guilds after this guild ID
        :return: List[guilds]
        """
        params: Dict[str, Union[int, str]] = {"limit": limit}

        if before:
            params["before"] = before
        if after:
            params["after"] = after
        return await self.request(Route("GET", "/users/@me/guilds", params=params))

    async def get_guild(self, guild_id: Snowflake_Type, with_counts: Optional[bool] = True) -> dict:
        """
        Get the guild object for the given ID.

        :param guild_id: the id of the guild
        :param with_counts: when `true`, will return approximate member and presence counts for the guild
        :return: a guild object
        """
        return await self.request(
            Route("GET", f"/guilds/{guild_id}"), params={"with_counts": int(with_counts)}  # type: ignore
        )

    async def get_member(self, guild_id: Snowflake_Type, user_id: Snowflake_Type) -> Dict:
        """
        Get a member of a guild by ID.

        :param guild_id: The id of the guild
        :param user_id: The user id to grab
        :return:
        """
        return await self.request(Route("GET", f"/guilds/{guild_id}/members/{user_id}"))

    async def get_channels(self, guild_id: Snowflake_Type) -> List[Dict]:
        """
        Get a guilds channels.

        :param guild_id: the id of the guild
        :return:
        """
        return await self.request(Route("GET", f"/guilds/{guild_id}/channels"))

    async def get_slash_commands(
        self, application_id: Snowflake_Type, guild_id: Optional[Snowflake_Type] = None
    ) -> List[Dict]:
        """
        Get all SlashCommands for this application from discord.

        :param application_id: the what application to query
        :param guild_id: specify a guild to get commands from
        :return:
        """
        if not guild_id:
            return await self.request(Route("GET", f"/applications/{application_id}/commands"))
        return await self.request(Route("GET", f"/applications/{application_id}/guilds/{guild_id}/commands"))

    # endregion

    async def create_message(
        self,
        channel_id: Snowflake_Type,
        content: Optional[str],
        tts: Optional[bool] = False,
        embeds: Optional[List[Dict]] = None,
        components: Optional[List[dict]] = None,
    ) -> Any:
        """Send a message to the specified channel. Incomplete."""
        # todo: Complete this
        payload: Dict[str, Any] = {}

        if content:
            payload["content"] = content
        if tts:
            payload["tts"] = tts
        if embeds:
            payload["embeds"] = embeds
        if components:
            payload["components"] = components
        return await self.request(Route("POST", f"/channels/{channel_id}/messages"), json=payload)
