import asyncio
import logging
import time
from collections import defaultdict
from typing import (
    TYPE_CHECKING,
)

import naff.api.events as events
from naff.client.const import logger_name, MISSING
from naff.models import (
    Guild,
    to_snowflake,
)
from naff.models.naff.listener import Listener
from naff.client.client import Client
from naff.api.gateway.state import ConnectionState

if TYPE_CHECKING:
    from naff.models import Snowflake_Type

__all__ = ("AutoShardedClient",)

from ..api.gateway.gateway import GatewayClient

log = logging.getLogger(logger_name)


class AutoShardedClient(Client):
    def __init__(self, *args, **kwargs) -> None:
        if "total_shards" not in kwargs:
            self.auto_sharding = True
        else:
            self.auto_sharding = False

        super().__init__(*args, **kwargs)

        self._connection_state = None

        self._connection_states: list[ConnectionState] = []

        self.max_start_concurrency: int = 1

    @property
    def gateway_started(self) -> bool:
        """Returns if the gateway has been started in all shards."""
        return all(state.gateway_started.is_set() for state in self._connection_states)

    async def stop(self) -> None:
        """Shutdown the bot."""
        log.debug("Stopping the bot.")
        self._ready.clear()
        await self.http.close()
        await asyncio.gather(*(state.stop() for state in self._connection_states))

    def get_guild_websocket(self, id: "Snowflake_Type") -> GatewayClient:
        shard_id = (id >> 22) % self.total_shards
        return next((state for state in self._connection_states if state.shard_id == shard_id), MISSING).gateway

    def get_shards_guild(self, shard_id: int) -> list[Guild]:
        """Returns the guilds that the specified shard can see"""
        return [guild for key, guild in self.cache.guild_cache.items() if ((key >> 22) % self.total_shards) == shard_id]

    @Listener.create()
    async def _on_websocket_ready(self, event: events.RawGatewayEvent) -> None:
        """
        Catches websocket ready and determines when to dispatch the client `READY` signal.

        Args:
            event: The websocket ready packet
        """
        connection_data = event.data
        expected_guilds = {to_snowflake(guild["id"]) for guild in connection_data["guilds"]}
        shard_id, total_shards = connection_data["shard"]
        connection_state = next((state for state in self._connection_states if state.shard_id == shard_id), None)

        if len(expected_guilds) != 0:
            while True:
                try:
                    await asyncio.wait_for(self._guild_event.wait(), self.guild_event_timeout)
                except asyncio.TimeoutError:
                    log.warning("Timeout waiting for guilds cache: Not all guilds will be in cache")
                    break
                self._guild_event.clear()
                if all(self.cache.get_guild(g_id) is not None for g_id in expected_guilds):
                    # all guilds cached
                    break

            if self.fetch_members:
                log.info(f"Shard {shard_id} is waiting for members to be chunked")
                await asyncio.gather(*(guild.chunked.wait() for guild in self.guilds if guild.id in expected_guilds))
        else:
            log.warning(
                f"Shard {shard_id} reports it has 0 guilds, this is an indicator you may be using too many shards"
            )
        # noinspection PyProtectedMember
        connection_state._shard_ready.set()
        log.debug(f"Shard {shard_id} is now ready")
        # noinspection PyProtectedMember
        await asyncio.gather(*[shard._shard_ready.wait() for shard in self._connection_states])

        # run any pending startup tasks
        if self.async_startup_tasks:
            try:
                await asyncio.gather(*self.async_startup_tasks)
            except Exception as e:
                await self.on_error("async-extension-loader", e)

        # cache slash commands
        if not self._startup:
            await self._init_interactions()

        if not self._ready.is_set():
            self._ready.set()
            if not self._startup:
                self._startup = True
                self.dispatch(events.Startup())
            self.dispatch(events.Ready())

    async def astart(self, token) -> None:
        """
        Asynchronous method to start the bot.

        Args:
            token: Your bot's token
        """
        log.debug("Starting http client...")
        await self.login(token)

        tasks = []

        # Sort shards into their respective ratelimit buckets
        shard_buckets = defaultdict(list)
        for shard in self._connection_states:
            bucket = str(shard.shard_id % self.max_start_concurrency)
            shard_buckets[bucket].append(shard)

        for bucket in shard_buckets.values():
            for shard in bucket:
                log.debug(f"Starting {shard.shard_id}")
                start = time.perf_counter()
                tasks.append(asyncio.create_task(shard.start()))

                if self.max_start_concurrency == 1:
                    # connection ratelimiting when discord has asked for one connection concurrently
                    # we could wait for `state._shard_ready`, but by waiting on the raw websocket ready
                    # we can start our subsequent shards sooner - speeding up startup
                    while not shard.gateway:
                        await asyncio.sleep(0.1)
                    # noinspection PyProtectedMember
                    await shard.gateway._ready.wait()
                    await asyncio.sleep(5.1 - (time.perf_counter() - start))

            # wait for shards to finish starting
            # noinspection PyProtectedMember
            await asyncio.gather(*[shard._shard_ready.wait() for shard in self._connection_states])

        try:
            await asyncio.gather(*tasks)
        finally:
            await self.stop()

    async def login(self, token) -> None:
        """
        Login to discord via http.

        !!! note
            You will need to run Naff.start_gateway() before you start receiving gateway events.

        Args:
            token str: Your bot's token

        """
        await super().login(token)
        data = await self.http.get_gateway_bot()

        self.max_start_concurrency = data["session_start_limit"]["max_concurrency"]
        if self.auto_sharding:
            self.total_shards = data["shards"]
        elif data["shards"] != self.total_shards:
            recommended_shards = data["shards"]
            log.info(
                f"Discord recommends you start with {recommended_shards} shard{'s' if recommended_shards != 1 else ''} instead of {self.total_shards}"
            )

        log.debug(f"Starting bot with {self.total_shards} shard{'s' if self.total_shards != 1 else ''}")
        self._connection_states: list[ConnectionState] = [
            ConnectionState(self, self.intents, shard_id) for shard_id in range(self.total_shards)
        ]