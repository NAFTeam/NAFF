import asyncio
import logging
import time
from types import TracebackType
from typing import TYPE_CHECKING, TypeVar, Coroutine, Any, Optional, Type, Dict, Union
from urllib.parse import quote as _uriquote

import orjson

import aiohttp

from discord_snakes.errors import *
from discord_snakes.models.discord_objects.user import User
from discord_snakes.models.route import Route
from discord_snakes.models.snowflake import Snowflake
from discord_snakes.utils.utils_json import response_decode
from discord_snakes.const import __repo_url__, __version__, __py_version__, logger_name

log = logging.getLogger(logger_name)

T = TypeVar("T")
BE = TypeVar("BE", bound=BaseException)
MU = TypeVar("MU", bound="MaybeUnlock")
Response = Coroutine[Any, Any, T]


class DiscordClientWebSocketResponse(aiohttp.ClientWebSocketResponse):
    async def close(self, *, code: int = 4000, message: bytes = b"") -> bool:
        return await super().close(code=code, message=message)


class MaybeUnlock:
    def __init__(self, lock: asyncio.Lock) -> None:
        self.lock: asyncio.Lock = lock
        self._unlock: bool = True

    def __enter__(self: MU) -> MU:
        return self

    def defer(self) -> None:
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
    """A http client for sending requests to the Discord API"""

    def __init__(
        self, connector: Optional[aiohttp.BaseConnector] = None, loop: Optional[asyncio.AbstractEventLoop] = None
    ):
        self.connector = connector
        self.loop = asyncio.get_event_loop() if loop is None else loop
        self.__session: aiohttp.ClientSession = None
        self._retries: int = 5
        self.token: Optional[str] = None

        self.user_agent: str = (
            f"DiscordBot ({__repo_url__} {__version__} Python/{__py_version__}) aiohttp/{aiohttp.__version__}"
        )

    def __del__(self):
        if self.__session and not self.__session.closed:
            self.loop.run_until_complete(self.__session.close())

    async def request(self, route: Route, **kwargs: Any):
        """Make a request to the discord API"""
        lock = asyncio.Lock()

        headers: Dict[str, str] = {"User-Agent": self.user_agent}

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
        with MaybeUnlock(lock) as maybe_unlock:
            for tries in range(self._retries):
                try:
                    async with self.__session.request(route.method, route.url, **kwargs) as response:
                        log.debug(f"{route.method} {route.url} with {kwargs.get('data')} returned {response.status}")

                        data = await response_decode(response)

                        # ratelimits
                        remaining = response.headers.get("X-Ratelimit-Remaining")
                        if remaining == "0" or response.status == 429:
                            raise RateLimited(route=route, code=response.status, resp=response)

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

    async def login(self, token: str):
        self.__session = aiohttp.ClientSession(
            connector=self.connector, ws_response_class=DiscordClientWebSocketResponse
        )
        self.token = token
        try:
            return await self.request(Route("GET", "/users/@me"))
        except HTTPError as e:
            if e.status_code == 401:
                raise HTTPError("An improper was token passed", e.route, e.status_code, e.response) from e
            raise

    async def close(self):
        if self.__session:
            await self.__session.close()

    async def logout(self):
        return await self.request(Route("POST", "/auth/logout"))

    async def get_gateway(self):
        try:
            data = await self.request(Route("GET", "/gateway"))
        except HTTPError as exc:
            raise GatewayNotFound from exc
        return "{0}?encoding={1}&v=8&compress=zlib-stream".format(data["url"], "json")

    async def websock_connect(self, url: str):
        return await self.__session.ws_connect(
            url, timeout=30, max_msg_size=0, autoclose=False, headers={"User-Agent": self.user_agent}, compress=0
        )

    async def get_user(self, user_id: Snowflake):
        return await self.request(Route("GET", "/users/{user_id}", user_id=user_id))

    async def send_typing(self, channel_id: Snowflake):
        return await self.request(Route("POST", "/channels/{channel_id}/typing", channel_id=channel_id))
