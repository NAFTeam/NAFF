"""
This file outlines the interaction between snek and Discord's Gateway API.
"""
import asyncio
import collections
import logging
import random
import sys
import time
import zlib
from types import TracebackType
from typing import TypeVar, TYPE_CHECKING

from aiohttp import WSMsgType

from dis_snek.const import logger_name
from dis_snek.errors import WebSocketClosed
from dis_snek.models import events, Snowflake_Type, CooldownSystem, to_snowflake
from dis_snek.models.enums import Status
from dis_snek.models.enums import WebSocketOPCodes as OPCODE
from dis_snek.utils.input_utils import OverriddenJson
from dis_snek.utils.serializer import dict_filter_none

if TYPE_CHECKING:
    from dis_snek.state import ConnectionState

log = logging.getLogger(logger_name)


SELF = TypeVar("SELF", bound="WebsocketClient")


class GatewayRateLimit:
    def __init__(self) -> None:
        self.lock = asyncio.Lock()
        # docs state 120 calls per 60 seconds, this is set conservatively to 110 per 60 seconds.
        self.cooldown_system = CooldownSystem(110, 60)

    async def rate_limit(self) -> None:
        async with self.lock:
            if not self.cooldown_system.acquire_token():
                await asyncio.sleep(self.cooldown_system.get_cooldown_time())


class WebsocketClient:
    """
    Abstraction over one gateway connection.

    Multiple `WebsocketClient` instances can be used to implement same-process sharding.

    Attributes:
        buffer: A buffer to hold incoming data until its complete
        sequence: The sequence of this connection
        session_id: The session ID of this connection
    """

    __slots__ = (
        "state",
        "ws",
        "shard",
        "_zlib",
        "rl_manager",
        "chunk_cache",
        "_trace",
        "heartbeat_interval",
        "sequence",
        "session_id",
        "latency",
        "_race_lock",
        "_closed",
        "_keep_alive",
        "_kill_bee_gees",
        "_last_heartbeat",
        "_acknowledged",
        "_entered",
    )

    def __init__(self, state: "ConnectionState", shard: tuple[int, int]) -> None:
        self.state = state
        self.ws = None
        self.shard = shard

        self._zlib = zlib.decompressobj()

        self.rl_manager = GatewayRateLimit()
        self.chunk_cache = {}

        self._trace = []
        self.heartbeat_interval = None
        self.sequence = None
        self.session_id = None

        self.latency = collections.deque(maxlen=10)

        # This lock needs to be held to send something over the gateway, but is also held when
        # reconnecting. That way there's no race conditions between sending and reconnecting.
        self._race_lock = asyncio.Lock()
        # Then this event is used so that receive() can wait for the reconnecting to complete.
        self._closed = asyncio.Event()

        self._keep_alive = None
        self._kill_bee_gees = asyncio.Event()
        self._last_heartbeat = 0
        self._acknowledged = asyncio.Event()
        self._acknowledged.set()  # Initialize it as set

        # Santity check, it is extremely important that an instance isn't reused.
        self._entered = False

    @property
    def loop(self):
        return self.state.client.loop

    async def __aenter__(self: SELF) -> SELF:
        if self._entered:
            raise RuntimeError("An instance of 'WebsocketClient' cannot be re-used!")

        self._entered = True

        self.ws = await self.state.client.http.websocket_connect(self.state.gateway_url)
        self._closed.set()

        hello = await self.receive()
        self.heartbeat_interval = hello["d"]["heartbeat_interval"] / 1000

        self._keep_alive = asyncio.create_task(self._start_bee_gees())

        await self._identify()

        return self

    async def __aexit__(
        self, exc_type: type[BaseException] | None, exc_val: BaseException | None, traceback: TracebackType | None
    ) -> None:
        if self._keep_alive is not None:
            self._kill_bee_gees.set()

        if self.ws is not None:
            # We could be cancelled here, it is extremely important that we close the
            # WebSocket either way, hence the try/except.
            try:
                await self._race_lock.acquire()
            except asyncio.CancelledError:
                if self._keep_alive is not None:
                    self._keep_alive.cancel()

                raise
            finally:
                await self.ws.close(code=1000)

    @property
    def average_latency(self) -> float:
        """Get the average latency of the connection."""
        if self.latency:
            return sum(self.latency) / len(self.latency)
        else:
            return float("inf")

    async def send(self, data: str, bypass=False) -> None:
        """
        Send data to the gateway.

        Parameters:
            data: The data to send
            bypass: Should the rate limit be ignored for this send (used for heartbeats)
        """
        if self.ws is None:
            raise RuntimeError

        if not bypass:
            await self.rl_manager.rate_limit()

        log.debug(f"Sending data to gateway: {data}")
        async with self._race_lock:
            await self.ws.send_str(data)

    async def send_json(self, data: dict, bypass=False) -> None:
        """
        Send json data to the gateway.

        Parameters:
            data: The data to send
            bypass: Should the rate limit be ignored for this send (used for heartbeats)

        """
        serialized = OverriddenJson.dumps(data)
        await self.send(serialized, bypass)

    async def receive(self) -> dict:
        """Receive a full event payload from the WebSocket."""

        buffer = bytearray()

        while True:
            # If we are currently reconnecting, wait for it to complete.
            await self._closed.wait()

            resp = await self.ws.receive()

            if resp.type == WSMsgType.CLOSE:
                log.debug(f"Disconnecting from gateway! Reason: {resp.data}::{resp.extra}")
                if resp.data >= 4000:
                    # This should propogate to __aexit__() which will forcefully shutdown everything
                    # and cleanup correctly.
                    raise WebSocketClosed(resp.data)

                await self.reconnect(code=1000)
                continue

            elif resp.type is WSMsgType.CLOSED:
                if not self._closed.is_set():
                    # Because we are waiting for the even before we receive, this shouldn't be
                    # possible - the CLOSING message should be returned instead. Either way, if this
                    # is possible after all we can just wait for the event to be set.
                    await self._closed.wait()
                else:
                    # This is an odd corner-case where the underlying socket connection was closed
                    # unexpectedly without communicating the WebSocket closing handshake. We'll have
                    # to reconnect ourselves.
                    await self.reconnect()

            elif resp.type is WSMsgType.CLOSING:
                # This happens when the keep-alive handler is reconnecting the connection even
                # though we waited for the event before hand, because it got to run while we waited
                # for data to come in. We can just wait for the event again.
                await self._closed.wait()
                continue

            if isinstance(resp.data, bytes):
                buffer.extend(resp.data)

            if resp.data is None:
                continue

            if len(resp.data) < 4 or resp.data[-4:] != b"\x00\x00\xff\xff":
                # message isn't complete yet, wait
                continue

            msg = self._zlib.decompress(buffer)

            msg = msg.decode("utf-8")
            msg = OverriddenJson.loads(msg)

            return msg

    async def reconnect(self, *, resume: bool = False, code: int = 1012) -> None:
        if self.ws is None:
            raise RuntimeError

        async with self._race_lock:
            self._closed.clear()

            await self.ws.close(code=code)
            self.ws = None

            self.ws = await self.state.client.http.websocket_connect(self.state.gateway_url)

            hello = await self.receive()
            self.heartbeat_interval = hello["d"]["heartbeat_interval"] / 1000

            if not resume:
                await self._identify()
            else:
                await self._resume_connection()

            self._closed.set()
            self._acknowledged.set()

    async def _start_bee_gees(self) -> None:
        if self.heartbeat_interval is None:
            raise RuntimeError

        await asyncio.sleep(self.heartbeat_interval * random.uniform(0, 0.5))

        log.debug(f"Sending heartbeat every {self.heartbeat_interval} seconds")
        while not self._kill_bee_gees.is_set():
            if not self._acknowledged.is_set():
                log.warning(
                    f"Heartbeat has not been acknowledged for {self.heartbeat_interval} seconds,"
                    " likely zombied connection. Reconnect!"
                )

                await self.reconnect(resume=True)

            self._acknowledged.clear()
            await self.send_heartbeat()
            self._last_heartbeat = time.perf_counter()

            try:
                # wait for next iteration, accounting for latency
                await asyncio.wait_for(self._kill_bee_gees.wait(), timeout=self.heartbeat_interval)
            except asyncio.TimeoutError:
                continue
            else:
                return

    async def run(self) -> None:
        """Start receiving events from the websocket."""
        while True:
            msg = await self.receive()
            if not msg:
                return

            op = msg.get("op")
            data = msg.get("d")
            seq = msg.get("s")
            event = msg.get("t")

            if seq:
                self.sequence = seq

            if op == OPCODE.DISPATCH:
                asyncio.create_task(self.dispatch_event(data, seq, event))
                continue

            # This may try to reconnect the connection so it is best to wait
            # for it to complete before receiving more - that way there's less
            # possible race conditions to consider.
            await self.dispatch_opcode(data, op)

    async def dispatch_opcode(self, data, op):
        match op:

            case OPCODE.HEARTBEAT:
                return await self.send_heartbeat()

            case OPCODE.HEARTBEAT_ACK:
                self.latency.append(time.perf_counter() - self._last_heartbeat)

                if self._last_heartbeat != 0 and self.latency[-1] >= 15:
                    log.warning(
                        f"High Latency! shard ID {self.shard[0]} heartbeat took {self.latency[-1]:.1f}s to be acknowledged!"
                    )
                else:
                    log.debug(f"❤ Heartbeat acknowledged after {self.latency[-1]:.5f} seconds")

                return self._acknowledged.set()

            case OPCODE.RECONNECT:
                log.info("Gateway requested reconnect. Reconnecting...")
                return await self.reconnect(resume=True)

            case OPCODE.INVALIDATE_SESSION:
                log.warning("Gateway has invalidated session! Reconnecting...")
                return await self.reconnect(resume=data["d"])

            case _:
                return log.debug(f"Unhandled OPCODE: {op} = {OPCODE(op).name}")

    async def dispatch_event(self, data, seq, event):
        match event:
            case "READY":
                self._trace = data.get("_trace", [])
                self.sequence = seq
                self.session_id = data["session_id"]
                log.info("Connected to gateway!")
                log.debug(f" Session ID: {self.session_id} Trace: {self._trace}")
                return self.state.client.dispatch(events.WebsocketReady(data))

            case "RESUMED":
                log.debug(f"Successfully resumed connection! Session_ID: {self.session_id}")
                return self.state.client.dispatch(events.Resume())

            case "GUILD_MEMBERS_CHUNK":
                return self.loop.create_task(self._process_member_chunk(data))

            case _:
                # the above events are "special", and are handled by the gateway itself, the rest can be dispatched
                event_name = f"raw_{event.lower()}"
                processor = self.state.client.processors.get(event_name)
                if processor:
                    try:
                        asyncio.create_task(processor(events.RawGatewayEvent(data, override_name=event_name)))
                    except Exception as ex:
                        log.error(f"Failed to run event processor for {event_name}: {ex}")
                else:
                    log.debug(f"No processor for `{event_name}`")

        self.state.client.dispatch(events.RawGatewayEvent(data, override_name="raw_socket_receive"))

    async def _identify(self) -> None:
        """Send an identify payload to the gateway."""
        if self.ws is None:
            raise RuntimeError

        payload = {
            "op": OPCODE.IDENTIFY,
            "d": {
                "token": self.state.client.http.token,
                "intents": self.state.intents,
                "shard": self.shard,
                "large_threshold": 250,
                "properties": {"$os": sys.platform, "$browser": "dis.snek", "$device": "dis.snek"},
                "presence": self.state.presence,
            },
            "compress": True,
        }

        serialized = OverriddenJson.dumps(payload)
        await self.ws.send_str(serialized)

        log.debug(
            f"Shard ID {self.shard[0]} has identified itself to Gateway, requesting intents: {self.state.intents}!"
        )

    async def _resume_connection(self) -> None:
        """Send a resume payload to the gateway."""
        if self.ws is None:
            raise RuntimeError

        payload = {
            "op": OPCODE.RESUME,
            "d": {"token": self.state.client.http.token, "seq": self.sequence, "session_id": self.session_id},
        }

        serialized = OverriddenJson.dumps(payload)
        await self.ws.send_str(serialized)

        log.debug("Client is attempting to resume a connection")

    async def send_heartbeat(self) -> None:
        """Send a heartbeat to the gateway."""
        await self.send_json({"op": OPCODE.HEARTBEAT, "d": self.sequence}, True)
        log.debug(f"❤ Shard {self.shard[0]} is sending a Heartbeat")

    async def change_presence(self, activity=None, status: Status = Status.ONLINE, since=None):
        payload = dict_filter_none(
            {
                "since": int(since if since else time.time() * 1000),
                "activities": [activity] if activity else [],
                "status": status,
                "afk": False,
            }
        )
        await self.send_json({"op": OPCODE.PRESENCE, "d": payload})

    async def request_member_chunks(
        self, guild_id: Snowflake_Type, query="", *, limit, user_ids=None, presences=False, nonce=None
    ):
        payload = {
            "op": OPCODE.REQUEST_MEMBERS,
            "d": dict_filter_none(
                {
                    "guild_id": guild_id,
                    "presences": presences,
                    "limit": limit,
                    "nonce": nonce,
                    "user_ids": user_ids,
                    "query": query,
                }
            ),
        }
        await self.send_json(payload)

    async def _process_member_chunk(self, chunk: dict):

        g_id = to_snowflake(chunk.get("guild_id"))
        guild = self.state.client.cache.guild_cache.get(g_id)

        if guild.chunked.is_set():
            # ensure the guild object "knows" its being chunked
            guild.chunked.clear()

        if g_id not in self.chunk_cache:
            self.chunk_cache[g_id] = chunk.get("members")
        else:
            self.chunk_cache[g_id] = self.chunk_cache[g_id] + chunk.get("members")

        if chunk.get("chunk_index") != chunk.get("chunk_count") - 1:
            return log.debug(f"Caching chunk of {len(chunk.get('members'))} members for {g_id}")
        else:
            members = self.chunk_cache.get(g_id, chunk.get("members"))

            log.info(f"Processing {len(members)} members for {g_id}")

            s = time.monotonic()
            start_time = time.perf_counter()

            for i, member in enumerate(members):
                self.state.client.cache.place_member_data(g_id, member)
                if (time.monotonic() - s) > 0.05:
                    # look, i get this *could* be a thread, but because it needs to modify data in the main thread,
                    # it is still blocking. So by periodically yielding to the event loop, we can avoid blocking, and still
                    # process this data properly
                    await asyncio.sleep(0)
                    s = time.monotonic()

            total_time = time.perf_counter() - start_time
            self.chunk_cache.pop(g_id, None)
            log.info(f"Cached members for {g_id} in {total_time:.2f} seconds")
            guild.chunked.set()
