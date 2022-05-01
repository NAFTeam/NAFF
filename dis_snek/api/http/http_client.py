"""This file handles the interaction with discords http endpoints."""
import asyncio
import logging
from typing import Any, Dict, Optional, Union
from urllib.parse import quote as _uriquote
from weakref import WeakValueDictionary

import aiohttp
from aiohttp import BaseConnector, ClientSession, ClientWebSocketResponse, FormData
from multidict import CIMultiDictProxy

from dis_snek.api.http.http_requests import (
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
    ScheduledEventsRequests,
)
from dis_snek.client.const import (
    __py_version__,
    __repo_url__,
    __version__,
    logger_name,
    MISSING,
    Absent,
    __api_version__,
)
from dis_snek.client.errors import DiscordError, Forbidden, GatewayNotFound, HTTPException, NotFound, LoginError
from dis_snek.client.utils.input_utils import response_decode
from dis_snek.client.utils.serializer import dict_filter_missing
from dis_snek.models import CooldownSystem
from .route import Route

__all__ = "HTTPClient"

log = logging.getLogger(logger_name)


class GlobalLock:
    """Manages the global ratelimit"""

    def __init__(self) -> None:
        self.cooldown_system: CooldownSystem = CooldownSystem(
            45, 1
        )  # global rate-limit is 50 per second, conservatively we use 45
        self._lock: asyncio.Lock = asyncio.Lock()

    async def rate_limit(self) -> None:
        async with self._lock:
            while not self.cooldown_system.acquire_token():
                await asyncio.sleep(self.cooldown_system.get_cooldown_time())

    async def lock(self, delta: float) -> None:
        """
        Lock the global lock for a given duration.

        Args:
            delta: The time to keep the lock acquired
        """
        await self._lock.acquire()
        await asyncio.sleep(delta)
        self._lock.release()


class BucketLock:
    """Manages the ratelimit for each bucket"""

    def __init__(self) -> None:
        self._lock: asyncio.Lock = asyncio.Lock()

        self.unlock_on_exit: bool = True

        self.bucket_hash: Optional[str] = None
        self.limit: int = -1
        self.remaining: int = -1
        self.delta: float = 0.0

    def __repr__(self) -> str:
        return f"<BucketLock: {self.bucket_hash or 'Generic'}>"

    @property
    def locked(self) -> bool:
        """Return True if lock is acquired."""
        return self._lock.locked()

    def unlock(self) -> None:
        """Unlock this bucket."""
        self._lock.release()

    def ingest_ratelimit_header(self, header: CIMultiDictProxy) -> None:
        """
        Ingests a discord rate limit header to configure this bucket lock.

        Args:
            header: A header from a http response
        """
        self.bucket_hash = header.get("x-ratelimit-bucket")
        self.limit = int(header.get("x-ratelimit-limit") or -1)
        self.remaining = int(header.get("x-ratelimit-remaining") or -1)
        self.delta = float(header.get("x-ratelimit-reset-after", 0.0))

    async def blind_defer_unlock(self) -> None:
        """Unlocks the BucketLock but doesn't wait for completion."""
        self.unlock_on_exit = False
        loop = asyncio.get_running_loop()
        loop.call_later(self.delta, self.unlock)

    async def defer_unlock(self) -> None:
        """Unlocks the BucketLock after a specified delay."""
        self.unlock_on_exit = False
        await asyncio.sleep(self.delta)
        self.unlock()

    async def __aenter__(self) -> None:
        await self._lock.acquire()

    async def __aexit__(self, *args) -> None:
        if self.unlock_on_exit and self._lock.locked():
            self.unlock()
        self.unlock_on_exit = True


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
    ScheduledEventsRequests,
):
    """A http client for sending requests to the Discord API."""

    def __init__(self, connector: Optional[BaseConnector] = None) -> None:
        self.connector: Optional[BaseConnector] = connector
        self.__session: Absent[Optional[ClientSession]] = MISSING
        self.token: Optional[str] = None
        self.global_lock: GlobalLock = GlobalLock()
        self._max_attempts: int = 3

        self.ratelimit_locks: WeakValueDictionary[str, BucketLock] = WeakValueDictionary()
        self._endpoints = {}

        self.user_agent: str = (
            f"DiscordBot ({__repo_url__} {__version__} Python/{__py_version__}) aiohttp/{aiohttp.__version__}"
        )

    def get_ratelimit(self, route: Route) -> BucketLock:
        """
        Get a route's rate limit bucket.

        Args:
            route: The route to fetch the ratelimit bucket for

        Returns:
            The BucketLock object for this route
        """
        if bucket_hash := self._endpoints.get(route.rl_bucket):
            # we have seen this route before, we know which bucket it is associated with
            lock = self.ratelimit_locks.get(bucket_hash)
            if lock:
                # if we have an active lock on this route, it'll still be in the cache
                # return that lock
                return lock
        # if no cached lock exists, return a new lock
        return BucketLock()

    def ingest_ratelimit(self, route: Route, header: CIMultiDictProxy, bucket_lock: BucketLock) -> None:
        """
        Ingests a ratelimit header from discord to determine ratelimit.

        Args:
            route: The route we're ingesting ratelimit for
            header: The rate limit header in question
            bucket_lock: The rate limit bucket for this route
        """
        bucket_lock.ingest_ratelimit_header(header)

        if bucket_lock.bucket_hash:
            # We only ever try and cache the bucket if the bucket hash has been set (ignores unlimited endpoints)
            log.debug(f"Caching ingested rate limit data for: {bucket_lock.bucket_hash}")
            self._endpoints[route.rl_bucket] = bucket_lock.bucket_hash
            self.ratelimit_locks[bucket_lock.bucket_hash] = bucket_lock

    async def request(
        self,
        route: Route,
        data: Absent[Union[dict, FormData]] = MISSING,
        reason: Absent[str] = MISSING,
        params: Absent[dict] = MISSING,
        **kwargs: Dict[str, Any],
    ) -> Any:
        """
        Make a request to discord.

        Args:
            route: The route to take
            json: A json payload to send in the request
            reason: Attach a reason to this request, used for audit logs

        """
        # Assemble headers
        kwargs["headers"] = {"User-Agent": self.user_agent}
        if self.token:
            kwargs["headers"]["Authorization"] = f"Bot {self.token}"
        if reason not in (None, MISSING):
            kwargs["headers"]["X-Audit-Log-Reason"] = _uriquote(reason, safe="/ ")

        if isinstance(data, (list, dict)):
            kwargs["headers"]["Content-Type"] = "application/json"

        # sanity check payload
        if isinstance(data, list):
            kwargs["json"] = [dict_filter_missing(x) if isinstance(x, dict) else x for x in data]
        elif isinstance(data, dict):
            kwargs["json"] = dict_filter_missing(data)
        elif isinstance(data, FormData):
            kwargs["data"] = data

        if isinstance(params, dict):
            kwargs["params"] = dict_filter_missing(params)

        lock = self.get_ratelimit(route)
        # this gets a BucketLock for this route.
        # If this endpoint has been used before, it will get an existing ratelimit for the respective buckethash
        # otherwise a brand-new bucket lock will be returned

        for attempt in range(self._max_attempts):
            async with lock:
                try:
                    await self.global_lock.rate_limit()
                    # prevent us exceeding the global rate limit by throttling http requests

                    if self.__session.closed:
                        await self.login(self.token)

                    async with self.__session.request(route.method, route.url, **kwargs) as response:
                        result = await response_decode(response)
                        self.ingest_ratelimit(route, response.headers, lock)

                        if response.status == 429:
                            # ratelimit exceeded

                            if result.get("global", False):
                                # if we get a global, that's pretty bad, this would usually happen if the user is hitting the api from 2 clients sharing a token
                                log.error(
                                    f"Bot has exceeded global ratelimit, locking REST API for {result.get('retry_after')} seconds"
                                )
                                await self.global_lock.lock(float(result.get("retry_after")))
                                continue
                            else:
                                # 429's are unfortunately unavoidable, but we can attempt to avoid them
                                # so long as these are infrequent we're doing well
                                log.warning(
                                    f"{route.endpoint} Has exceeded it's ratelimit ({lock.limit})! Reset in {lock.delta} seconds"
                                )
                                await lock.defer_unlock()  # lock this route and wait for unlock
                                continue
                        elif lock.remaining == 0:
                            # Last call available in the bucket, lock until reset
                            log.debug(
                                f"{route.endpoint} Has exhausted its ratelimit ({lock.limit})! Locking route for {lock.delta} seconds"
                            )
                            await lock.blind_defer_unlock()  # lock this route, but continue processing the current response

                        elif response.status in {500, 502, 504}:
                            # Server issues, retry
                            log.warning(
                                f"{route.endpoint} Received {response.status}... retrying in {1 + attempt * 2} seconds"
                            )
                            await asyncio.sleep(1 + attempt * 2)
                            continue

                        if not 300 > response.status >= 200:
                            await self._raise_exception(response, route, result)

                        log.debug(
                            f"{route.endpoint} Received {response.status} :: [{lock.remaining}/{lock.limit} calls remaining]"
                        )
                        return result
                except OSError as e:
                    if attempt < self._max_attempts - 1 and e.errno in (54, 10054):
                        await asyncio.sleep(1 + attempt * 2)
                        continue
                    raise

    async def _raise_exception(self, response, route, result) -> None:
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

        Args:
            token: the token to use

        Returns:
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
        if self.__session and not self.__session.closed:
            await self.__session.close()

    async def get_gateway(self) -> str:
        """
        Gets the gateway url.

        Returns:
            The gateway url

        """
        try:
            data: dict = await self.request(Route("GET", "/gateway"))
        except HTTPException as exc:
            raise GatewayNotFound from exc
        return "{0}?encoding={1}&v={2}&compress=zlib-stream".format(data["url"], "json", __api_version__)

    async def websocket_connect(self, url: str) -> ClientWebSocketResponse:
        """
        Connect to the websocket.

        Args:
            url: the url to connect to

        """
        return await self.__session.ws_connect(
            url, timeout=30, max_msg_size=0, autoclose=False, headers={"User-Agent": self.user_agent}, compress=0
        )
