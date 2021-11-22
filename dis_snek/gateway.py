"""
This file outlines the interaction between snek and Discord's Gateway API.
"""
import asyncio
import concurrent.futures
import logging
import random
import sys
import threading
import time
import zlib
from concurrent.futures import ThreadPoolExecutor
from typing import Any, List, Optional, TYPE_CHECKING

from aiohttp import WSMsgType

from dis_snek.const import logger_name, MISSING
from dis_snek.errors import WebSocketClosed, WebSocketRestart
from dis_snek.models import events, Snowflake_Type, CooldownSystem, to_snowflake
from dis_snek.models.enums import Status
from dis_snek.models.enums import WebSocketOPCodes as OPCODE
from dis_snek.utils.input_utils import OverriddenJson
from dis_snek.utils.serializer import dict_filter_none

if TYPE_CHECKING:
    from dis_snek import Snake

log = logging.getLogger(logger_name)


class GatewayRateLimit:
    def __init__(self):
        self.lock = asyncio.Lock()
        # docs state 120 calls per 60 seconds, this is set conservatively to 100 per 60 seconds.
        self.cooldown = CooldownSystem(100, 60)

    async def rate_limit(self):
        async with self.lock:
            if not self.cooldown.acquire_token():
                await asyncio.sleep(self.cooldown.get_cooldown_time())


class BeeGees(threading.Thread):
    """
    Keeps the gateway connection alive.

    ♫ Stayin' Alive ♫

    Parameters:
        ws WebsocketClient: WebsocketClient
        interval int: How often to send heartbeats -- dictated by discord
    """

    slots = ("ws", "interval", "timeout", "latency", "_last_ack", "_last_send", "_stop_ev")

    def __init__(self, ws: Any, interval: int, timeout: int = 60, heartbeat_timeout: int = 120) -> None:
        self.ws = ws
        self.interval: int = interval
        self.timeout: int = timeout
        self.latency: List[float] = []
        self._max_heartbeat_timeout = heartbeat_timeout

        self._last_ack: float = 0
        self._last_send: float = 0
        self._stop_ev: threading.Event = threading.Event()

        super().__init__()
        self.daemon = True

    def run(self) -> None:
        """Start automatically sending heartbeats to discord."""
        log.debug(f"Sending heartbeat every {self.interval} seconds")
        while not self._stop_ev.is_set():
            wait_time = 0
            while wait_time < self._max_heartbeat_timeout:
                try:
                    f = asyncio.run_coroutine_threadsafe(self.ws.send_heartbeat(), loop=self.ws.loop)
                    f.result(10)
                except concurrent.futures.TimeoutError:
                    wait_time += 10
                    log.warning(f"Failed to send heartbeat! Blocked for {wait_time} seconds")
                else:
                    self._last_send = time.perf_counter()
                    time.sleep(self.interval)
                    continue
            log.critical(f"Unable to send heartbeat for {wait_time} seconds, no longer sending heartbeats.")
            self.stop()

    def stop(self) -> None:
        """Stop sending heartbeats."""
        self._stop_ev.set()

    def ack(self) -> None:
        """Log discord ack the heartbeat."""
        ack_time = self._last_ack = time.perf_counter()

        self.latency.append(ack_time - self._last_send)
        if len(self.latency) > 10:
            self.latency.pop(0)

        if self._last_send != 0 and self.latency[-1] > 10:
            log.warning(f"Can't keep up! shard ID {0} websocket is {self.latency[-1]:.1f}s behind.")
        else:
            log.debug(f"Heartbeat acknowledged after {self.latency[-1]:.1f} seconds")


class WebsocketClient:
    """
    Manages the connection to discord's websocket.

    Parameters:
        session_id: The session_id to use, if resuming
        sequence: The sequence to use, if resuming

    Attributes:
        buffer: A buffer to hold incoming data until its complete
        sequence: The sequence of this connection
        session_id: The session ID of this connection
    """

    __slots__ = (
        "_gateway",
        "ws",
        "session_id",
        "sequence",
        "buffer",
        "rl_manager",
        "_keep_alive",
        "_closed",
        "_zlib",
        "_max_heartbeat_timeout",
        "_trace",
        "_thread_pool",
    )

    def __init__(self, session_id: Optional[int] = None, sequence: Optional[int] = None) -> None:
        self.session_id = session_id
        self.sequence = sequence

        self.buffer = bytearray()
        self._zlib = zlib.decompressobj()
        self._keep_alive = MISSING

        self._max_heartbeat_timeout = 120
        self.rl_manager = GatewayRateLimit()
        self._thread_pool = ThreadPoolExecutor(max_workers=2)

        self._trace = []

        self._closed = False

    @property
    def loop(self):
        return self.client.loop

    @classmethod
    async def connect(
        cls,
        client: "Snake",
        session_id: Optional[int] = None,
        sequence: Optional[int] = None,
        presence: Optional[dict] = None,
    ):
        """
        Connect tot he discord gateway
        Args:
            client: The Snek Client
            session_id: The session id to use, if resuming
            sequence: The sequence to use, if resuming
            presence: The presence to login with
        """
        cls.client = client
        cls._gateway = await client.http.get_gateway()
        cls.presence = presence
        cls.ws = await client.http.websocket_connect(cls._gateway)
        client.dispatch(events.Connect())
        if session_id and sequence:
            # resume
            return cls(session_id, sequence)
        return cls()

    @property
    def latency(self) -> float:
        """Get the latency of the connection."""
        if self._keep_alive.latency:
            return self._keep_alive.latency[-1]
        else:
            return float("inf")

    @property
    def average_latency(self) -> float:
        """Get the average latency of the connection."""
        if self._keep_alive.latency:
            return sum(self._keep_alive.latency) / len(self._keep_alive.latency)
        else:
            return float("inf")

    async def send(self, data: str, bypass=False) -> None:
        """
        Send data to the gateway.

        Parameters:
            data: The data to send
            bypass: Should the rate limit be ignored for this send (used for heartbeats)
        """
        if not bypass:
            await self.rl_manager.rate_limit()
        log.debug(f"Sending data to gateway: {data}")
        await self.ws.send_str(data)

    async def send_json(self, data: dict, bypass=False) -> None:
        """
        Send json data to the gateway.

        Parameters:
            data: The data to send
            bypass: Should the rate limit be ignored for this send (used for heartbeats)

        """
        data = OverriddenJson.dumps(data)
        await self.send(data, bypass)

    async def run(self) -> None:
        """Start receiving events from the websocket."""
        while not self.client.is_closed:
            resp = await self.ws.receive()
            msg = resp.data

            if resp.type == WSMsgType.CLOSE:
                log.debug(f"Disconnecting from gateway! Reason: {resp.data}::{resp.extra}")
                await self.close(msg)
                return

            if resp.type == WSMsgType.CLOSING:
                return

            if resp.type == WSMsgType.CLOSED:
                raise WebSocketClosed(1000)

            if isinstance(resp.data, bytes):
                self.buffer.extend(msg)

            if len(msg) < 4 or msg[-4:] != b"\x00\x00\xff\xff":
                # message isn't complete yet, wait
                continue

            msg = self._zlib.decompress(self.buffer)
            self.buffer = bytearray()

            msg = msg.decode("utf-8")
            msg = OverriddenJson.loads(msg)
            # log.debug(f"Websocket Event: {msg}")

            await self._dispatch(msg)
        await self.close()

    async def _dispatch(self, msg: dict):
        op = msg.get("op")
        data = msg.get("d")
        seq = msg.get("s")
        event = msg.get("t")

        if seq:
            self.sequence = seq

        if op != OPCODE.DISPATCH:
            if op == OPCODE.HELLO:
                self._keep_alive = BeeGees(ws=self, interval=data["heartbeat_interval"] / 1000)
                self.loop.call_later(self._keep_alive.interval * random.uniform(0, 0.5), self._keep_alive.start)
                if not self.session_id:
                    return await self.identify()
                return await self.resume()
            elif op == OPCODE.HEARTBEAT_ACK:
                return self._keep_alive.ack()
            elif op in (OPCODE.INVALIDATE_SESSION | OPCODE.RECONNECT):
                log.debug(f"Reconnecting to discord due to opcode {op}::{OPCODE(op).name}")
                if data is True or op == OPCODE.RECONNECT:
                    await self.close(code=1001)
                    raise WebSocketRestart(True)
                self.session_id = self.sequence = None
                log.warning("Session has been invalidated")
                await self.close(code=1000)
                raise WebSocketRestart(False)
            else:
                return log.debug(f"Unhandled OPCODE: {op} = {OPCODE(op).name}")

        else:
            if event == "READY":
                self._trace = data.get("_trace", [])
                self.sequence = seq
                self.session_id = data["session_id"]
                log.debug(f"Successfully connected to Gateway! Trace: {self._trace} Session_ID: {self.session_id}")
                self._dispatch_soon(data, "websocket_ready")
                return
            elif event == "RESUMED":
                log.debug(f"Successfully resumed connection! Session_ID: {self.session_id}")
            elif event == "GUILD_MEMBERS_CHUNK":
                # await self.loop.run_in_executor(self._thread_pool, self._process_member_chunk, data)
                await self._process_member_chunk(data)
            else:
                self._dispatch_soon(msg, "raw_socket_receive")
            self._dispatch_soon(data, f"raw_{event.lower()}")

    def _dispatch_soon(self, data, name):
        self.loop.call_soon(lambda: self.client.dispatch(events.RawGatewayEvent(data, override_name=name)))

    def __del__(self) -> None:
        if not self._closed:
            self.loop.run_until_complete(self.close())

    async def close(self, code: int = 1000) -> None:
        """
        Close the connection to the gateway.

        Parameters:
            code: the close code to use
        """
        await self.ws.close(code=code)
        if isinstance(self._keep_alive, BeeGees):
            self._keep_alive.stop()
        self._closed = True

    async def identify(self) -> None:
        """Send an identify payload to the gateway."""
        payload = {
            "op": OPCODE.IDENTIFY,
            "d": {
                "token": self.client.http.token,
                "intents": self.client.intents,
                "large_threshold": 250,
                "properties": {"$os": sys.platform, "$browser": "dis.snek", "$device": "dis.snek"},
                "presence": self.presence,
            },
            "compress": True,
        }
        await self.send_json(payload)
        log.debug(f"Client has identified itself to Gateway, requesting intents: {self.client.intents}!")

    async def resume(self) -> None:
        """Send a resume payload to the gateway."""
        payload = {
            "op": OPCODE.RESUME,
            "d": {"token": self.client.http.token, "seq": self.sequence, "session_id": self.session_id},
        }
        await self.send_json(payload)
        self.client.dispatch(events.Resume())
        self._dispatch_soon(None, events.Resume())
        log.debug("Client is attempting to resume a connection")

    async def send_heartbeat(self) -> None:
        """Send a heartbeat to the gateway."""
        await self.send_json({"op": OPCODE.HEARTBEAT, "d": self.sequence}, True)
        log.debug(f"Keeping Shard ID {0} alive with sequence {self.sequence}")

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
        log.debug(f"Processing chunk of {len(chunk.get('members'))} members for {g_id}")
        data = {}

        s = time.monotonic()

        for i, member in enumerate(chunk.get("members")):
            self.client.cache.place_member_data(g_id, member)
            if (time.monotonic() - s) > 0.03:
                # look, i get this *could* be a thread, but because it needs to modify data in the main thread,
                # it is still blocking. So by periodically yielding to the event loop, we can avoid blocking, and still
                # process this data properly
                await asyncio.sleep(0)
                s = time.monotonic()

        if chunk.get("chunk_index") == chunk.get("chunk_count") - 1:
            # if we have all expected chunks, mark the guild as "chunked"
            log.info(f"chunked {g_id}")
            guild = self.client.cache.guild_cache.get(g_id)
            guild.chunked.set()
