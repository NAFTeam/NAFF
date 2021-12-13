"""
This file handles the interaction with discords http endpoints.
"""
import asyncio
import datetime
import logging
import traceback
from collections import defaultdict
from typing import Any, Dict, Optional, TypeVar, Union
from urllib.parse import quote as _uriquote

import aiohttp  # type: ignore
from aiohttp import BaseConnector, ClientResponse, ClientSession, ClientWebSocketResponse, FormData
from multidict import CIMultiDictProxy  # type: ignore

from dis_snek.const import __py_version__, __repo_url__, __version__, logger_name, MISSING
from dis_snek.errors import DiscordError, Forbidden, GatewayNotFound, HTTPException, NotFound, LoginError
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
from dis_snek.models import CooldownSystem
from dis_snek.models.route import Route
from dis_snek.utils.input_utils import response_decode
from dis_snek.utils.serializer import dict_filter_missing

log = logging.getLogger(logger_name)


class GlobalLock:
    def __init__(self):
        self.cooldown_system: CooldownSystem = CooldownSystem(
            45, 1
        )  # global rate-limit is 50 per second, conservatively we use 45
        self.lock: asyncio.Lock = asyncio.Lock()

    async def rate_limit(self):
        async with self.lock:
            if not self.cooldown_system.acquire_token():
                await asyncio.sleep(self.cooldown_system.get_cooldown_time())


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
        self.__session: Optional[ClientSession] = MISSING
        self._retries: int = 5
        self.token: Optional[str] = None
        self.ratelimit_locks: Dict[str, asyncio.Lock] = defaultdict(asyncio.Lock)
        self.global_lock: GlobalLock = GlobalLock()

        self.user_agent: str = (
            f"DiscordBot ({__repo_url__} {__version__} Python/{__py_version__}) aiohttp/{aiohttp.__version__}"
        )

    def __del__(self):
        if self.__session and not self.__session.closed:
            self.loop.run_until_complete(self.__session.close())

    @staticmethod
    def _parse_ratelimit(header: CIMultiDictProxy[str]) -> dict:
        """
        Parse the ratelimit data into a more usable format.

        parameters:
            header: the header of the response
        :return:
        """
        return {
            "bucket": header.get("x-ratelimit-bucket"),
            "limit": int(header.get("x-ratelimit-limit") or -1),
            "remaining": int(header.get("x-ratelimit-remaining") or -1),
            "delta": float(header.get("x-ratelimit-reset-after", 0)),  # type: ignore
            "time": datetime.datetime.utcfromtimestamp(float(header.get("x-ratelimit-reset", 0))),  # type: ignore
        }

    async def request(
        self, route: Route, data: Union[dict, FormData] = MISSING, reason: str = MISSING, **kwargs: Dict[str, Any]
    ) -> Any:
        """
        Make a request to discord

        parameters:
            route: The route to take
            json: A json payload to send in the request
            reason: Attach a reason to this request, used for audit logs
        """
        # Assemble headers
        headers: Dict[str, str] = {"User-Agent": self.user_agent}
        if self.token not in (None, MISSING):
            headers["Authorization"] = "Bot " + self.token

        if isinstance(data, list):
            headers["Content-Type"] = "application/json"
            kwargs["json"] = [dict_filter_missing(x) if isinstance(x, dict) else x for x in data]
        elif isinstance(data, dict):
            headers["Content-Type"] = "application/json"
            kwargs["json"] = dict_filter_missing(data)
        elif isinstance(data, FormData):
            kwargs["data"] = data

        if reason not in (None, MISSING):
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
                if self.__session.closed:
                    await self.login(self.token)

                await self.global_lock.rate_limit()
                async with self.__session.request(route.method, route.url, **kwargs) as response:
                    result = await response_decode(response)
                    r_limit_data = self._parse_ratelimit(response.headers)

                    if response.status == 429:
                        # ratelimit exceeded
                        log.error(
                            f"{route.method}::{route.url}: Has exceeded ratelimit! Reset in {r_limit_data['delta']} seconds"
                        )
                        await asyncio.sleep(r_limit_data["delta"])
                        continue

                    elif r_limit_data["remaining"] == 0:
                        # ratelimit about to be exceeded, stop calls
                        log.debug(
                            f"{route.method}::{route.url}: Has exhausted its ratelimit! Locking route for {r_limit_data['delta']} seconds"
                        )
                        self.loop.call_later(r_limit_data["delta"], lock.release)

                    elif response.status in {500, 502, 504}:
                        # server issues, retry
                        log.warning(
                            f"{route.method}::{route.url}: Received {response.status}... retrying in {1 + tries * 2} seconds"
                        )
                        await asyncio.sleep(1 + tries * 2)
                        continue

                    if not 300 > response.status >= 200:
                        if not r_limit_data["remaining"] == 0:
                            lock.release()
                        await self._raise_exception(response, route, result)

                    # Success!
                    log.debug(f"{route.method}::{route.url}: Received {response.status}, releasing")
                    if not r_limit_data["remaining"] == 0:
                        lock.release()
                    return result
            except OSError as e:
                if tries < self._retries - 1 and e.errno in (54, 10054):
                    await asyncio.sleep(1 + tries * 2)
                    continue
                try:
                    lock.release()
                except RuntimeError:
                    pass
                raise
            except (Forbidden, NotFound, DiscordError, HTTPException):
                raise
            except Exception as e:
                try:
                    lock.release()
                except RuntimeError:
                    pass
                log.error("".join(traceback.format_exception(type(e), e, e.__traceback__)))
                break
        if lock.locked():
            # be clean and make sure we unlock
            lock.release()

    async def _raise_exception(self, response, route, result):
        log.error(f"{route.method}::{route.url}: {response.status}")

        if response.status == 403:
            raise Forbidden(response, response_data=result, route=route)
        elif response.status == 404:
            raise NotFound(response, response_data=result, route=route)
        elif response.status >= 500:
            raise DiscordError(response, response_data=result, route=route)
        else:
            raise HTTPException(response, response_data=result, route=route)

    async def request_cdn(self, url, asset) -> bytes:
        log.debug(f"{asset} requests {url} from CDN")
        async with self.__session.get(url) as response:
            if response.status == 200:
                return await response.read()
            await self._raise_exception(response, asset, await response_decode(response))

    async def login(self, token: str) -> dict:
        """
        "Login" to the gateway, basically validates the token and grabs user data.

        parameters:
            token: the token to use
        returns:
            The currently logged in bot's data
        """
        self.__session = ClientSession(connector=self.connector)
        self.token = token
        try:
            return await self.request(Route("GET", "/users/@me"))
        except HTTPException as e:
            if e.status == 401:
                raise LoginError("An improper token was passed") from e
            raise

    async def close(self) -> None:
        """Close the session."""
        if self.__session:
            await self.__session.close()

    async def get_gateway(self) -> str:
        """Get the gateway url."""
        try:
            data: dict = await self.request(Route("GET", "/gateway"))
        except HTTPException as exc:
            raise GatewayNotFound from exc
        return "{0}?encoding={1}&v=9&compress=zlib-stream".format(data["url"], "json")

    async def websocket_connect(self, url: str) -> ClientWebSocketResponse:
        """
        Connect to the websocket.

        parameters:
            url: the url to connect to
        """
        return await self.__session.ws_connect(
            url, timeout=30, max_msg_size=0, autoclose=False, headers={"User-Agent": self.user_agent}, compress=0
        )
