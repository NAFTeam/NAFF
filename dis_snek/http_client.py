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
from collections import defaultdict
from typing import Any, Coroutine, Dict, Optional, TypeVar, Union
from urllib.parse import quote as _uriquote

import aiohttp  # type: ignore
from aiohttp import BaseConnector, ClientResponse, ClientSession, ClientWebSocketResponse, FormData
from multidict import CIMultiDictProxy  # type: ignore

from dis_snek.const import __py_version__, __repo_url__, __version__, logger_name
from dis_snek.errors import DiscordError, Forbidden, GatewayNotFound, HTTPError, NotFound
from dis_snek.http_requests import (
    BotRequests,
    ChannelRequests,
    EmojiRequests,
    GuildRequests,
    InteractionRequests,
    MemberRequests,
    MessageRequests,
    ReactionRequests,
    StickerRequests,
    ThreadRequests,
    UserRequests,
    WebhookRequests,
)
from dis_snek.models.route import Route
from dis_snek.utils.input_utils import response_decode


log = logging.getLogger(logger_name)


T = TypeVar("T")
BE = TypeVar("BE", bound=BaseException)
MU = TypeVar("MU", bound="CanUnlock")
Response = Coroutine[Any, Any, T]


class DiscordClientWebSocketResponse(ClientWebSocketResponse):
    """Represents the websocket connection with discord."""

    async def close(self, *, code: int = 4000, message: bytes = b"") -> bool:
        """
        Close the connection.

        :param code: The close code to use
        :param message: A message to send within the close
        """
        return await super().close(code=code, message=message)


class HTTPClient(
    BotRequests,
    ChannelRequests,
    EmojiRequests,
    GuildRequests,
    InteractionRequests,
    MemberRequests,
    MessageRequests,
    ReactionRequests,
    StickerRequests,
    ThreadRequests,
    UserRequests,
    WebhookRequests,
):
    """A http client for sending requests to the Discord API."""

    def __init__(self, connector: Optional[BaseConnector] = None, loop: Optional[asyncio.AbstractEventLoop] = None):
        self.connector: Optional[BaseConnector] = connector
        self.loop = asyncio.get_event_loop() if loop is None else loop
        self.__session: Optional[ClientSession] = None
        self._retries: int = 5
        self.token: Optional[str] = None
        self.ratelimit_locks: Dict[str, asyncio.Lock] = defaultdict(asyncio.Lock)

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
            "delta": float(header.get("x-ratelimit-reset-after", 0)),  # type: ignore
            "time": datetime.datetime.utcfromtimestamp(float(header.get("x-ratelimit-reset", 0))),  # type: ignore
        }

    async def request(
        self, route: Route, data: Union[dict, FormData] = None, reason: str = None, **kwargs: Dict[str, Any]
    ) -> Any:
        """
        Make a request to discord
        :param route: The route to take
        :param json: A json payload to send in the request
        :param reason: Attach a reason to this request, used for audit logs
        """
        # Assemble headers
        headers: Dict[str, str] = {"User-Agent": self.user_agent}
        if self.token is not None:
            headers["Authorization"] = "Bot " + self.token
        if isinstance(data, (list, dict)):
            headers["Content-Type"] = "application/json"
            kwargs["json"] = data
        elif isinstance(data, FormData):
            kwargs["data"] = data
        if reason:
            headers["X-Audit-Log-Reason"] = _uriquote(reason, safe="/ ")

        kwargs["headers"] = headers

        if route.rl_bucket is not None:
            lock = self.ratelimit_locks[route.rl_bucket]
        else:
            lock = asyncio.Lock()

        response: Optional[ClientResponse] = None
        result: Optional[Union[Dict[str, Any], str]] = None

        await lock.acquire()
        for tries in range(self._retries):
            try:
                async with self.__session.request(route.method, route.url, **kwargs) as response:
                    log.debug(
                        f"{route.method} {route.url}{f' with {result}' if result else ''} returned {response.status}"
                    )
                    result = await response_decode(response)

                    remaining = response.headers.get("X-Ratelimit-Remaining")
                    if remaining == "0" and response.status != 429:
                        r_limit = self._parse_ratelimit(response.headers)
                        log.debug(
                            f"{route.method}::{route.url} has reached a rate limit... "
                            f"retrying in {r_limit['delta']} seconds"
                        )
                        self.loop.call_later(r_limit["delta"], lock.release)
                        return result

                    if 300 > response.status >= 200:
                        lock.release()
                        return result

                    if response.status in {500, 502, 504}:
                        log.warning(
                            f"{route.method}::{route.url} received {response.status}... retrying in {1 + tries * 2} seconds"
                        )
                        await asyncio.sleep(1 + tries * 2)
                        continue

                    await self._raise_exception(response, route)

            except OSError as e:
                if tries < self._retries - 1 and e.errno in (54, 10054):
                    await asyncio.sleep(1 + tries * 2)
                    continue
                lock.release()
                raise
            except (Forbidden, NotFound, DiscordError, HTTPError):
                lock.release()
                raise
            except Exception as e:
                lock.release()
                log.error("".join(traceback.format_exception(type(e), e, e.__traceback__)))
        lock.release()  # shouldn't get called, but here just to be clean

    async def _raise_exception(self, response, route):
        resp_text = await response.read()
        resp_text = resp_text.decode("utf-8")
        if response.status == 403:
            raise Forbidden(resp_text, route, response.status, response)
        elif response.status == 404:
            raise NotFound(resp_text, route, response.status, response)
        elif response.status >= 500:
            raise DiscordError(resp_text, route, response.status, response)
        else:
            raise HTTPError(resp_text, route, response.status, response)

    async def request_cdn(self, url, asset) -> bytes:
        log.debug(f"{asset} requests {url} from CDN")
        async with self.__session.get(url) as response:
            if response.status == 200:
                return await response.read()
            await self._raise_exception(response, asset)

    async def login(self, token: str) -> dict:
        """
        "Login" to the gateway, basically validates the token and grabs user data.

        :param token: the token to use
        :return: The currently logged in bot's data
        """
        self.__session = ClientSession(connector=self.connector, ws_response_class=DiscordClientWebSocketResponse)
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
