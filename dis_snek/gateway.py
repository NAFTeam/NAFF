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
from typing import Any, List, Optional, TYPE_CHECKING

import anyio
from aiohttp import WSMsgType

from dis_snek.const import logger_name, MISSING
from dis_snek.errors import WebSocketClosed
from dis_snek.models import events, Snowflake_Type, CooldownSystem, to_snowflake
from dis_snek.models.enums import Status
from dis_snek.models.enums import WebSocketOPCodes as OPCODE
from dis_snek.models.events import BaseEvent, RawGatewayEvent, WebsocketReady
from dis_snek.utils.input_utils import OverriddenJson
from dis_snek.utils.serializer import dict_filter_none

if TYPE_CHECKING:
    from dis_snek import Snake

log = logging.getLogger(logger_name)


class GatewayRateLimit:
    def __init__(self):
        self.lock = asyncio.Lock()
        # docs state 120 calls per 60 seconds, this is set conservatively to 110 per 60 seconds.
        self.cooldown = CooldownSystem(110, 60)

    async def rate_limit(self):
        async with self.lock:
            await asyncio.sleep(0.6)


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

        self._last_ack: float = time.perf_counter()
        self._last_send: float = 0
        self._stop_ev: threading.Event = threading.Event()

        super().__init__()
        self.daemon = True

    def run(self) -> None:
        """Start automatically sending heartbeats to discord."""
        log.debug(f"Sending heartbeat every {self.interval} seconds")
        while not self._stop_ev.is_set():

            if self._last_send and (self._last_ack + self._max_heartbeat_timeout) < time.perf_counter():
                log.warning(
                    f"Heartbeat has not been acknowledged for {self._max_heartbeat_timeout} seconds, likely zombied connection. Reconnect!"
                )
                self.stop()
                asyncio.run_coroutine_threadsafe(self.ws.close(resume=True), loop=self.ws.loop)
                continue

            wait_time = 0
            while wait_time < self._max_heartbeat_timeout:
                try:
                    f = asyncio.run_coroutine_threadsafe(self.ws.send_heartbeat(), loop=self.ws.loop)
                    f.result(10)
                except concurrent.futures.TimeoutError:
                    wait_time += 10
                    log.warning(f"Failed to send heartbeat! Blocked for {wait_time} seconds")
                    continue
                else:
                    self._last_send = time.perf_counter()
                    time.sleep(self.interval)
                    break
            if wait_time > self._max_heartbeat_timeout:
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

        if self._last_send != 0 and self.latency[-1] > 15:
            log.warning(f"High Latency! shard ID {0} heartbeat took {self.latency[-1]:.1f}s to be acknowledged!")
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

    # __slots__ = (
    #     "_gateway",
    #     "ws",
    #     "session_id",
    #     "sequence",
    #     "buffer",
    #     "rl_manager",
    #     "_keep_alive",
    #     "closed",
    #     "resume",
    #     "shutdown",
    #     "_zlib",
    #     "_max_heartbeat_timeout",
    #     "_trace",
    #     "_chunk_lock",
    # )

    def __init__(self, session_id: Optional[int] = None, sequence: Optional[int] = None) -> None:
        self.session_id = session_id
        self.sequence = sequence

        self.buffer = bytearray()
        self._zlib = zlib.decompressobj()
        self._keep_alive = MISSING

        self._max_heartbeat_timeout = 120
        self.rl_manager = GatewayRateLimit()
        self.chunk_cache = {}

        self._trace = []

        self.closed = asyncio.Event()
        self.resume = False
        self.shutdown = False

        self.processors = anyio.create_task_group()

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
        if not self.closed.is_set():
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
                if msg == 1000:
                    await self.close(1000)
                else:
                    await self.close(shutdown=True)
                    raise WebSocketClosed(msg)

                return

            if resp.type == WSMsgType.CLOSING:
                return

            if resp.type == WSMsgType.CLOSED:
                await self.close()

            if isinstance(resp.data, bytes):
                self.buffer.extend(msg)

            if len(msg) < 4 or msg[-4:] != b"\x00\x00\xff\xff":
                # message isn't complete yet, wait
                continue

            msg = self._zlib.decompress(self.buffer)
            self.buffer = bytearray()
            msg = msg.decode("utf-8")
            msg = OverriddenJson.loads(msg)

            op = msg.get("op")
            data = msg.get("d")
            seq = msg.get("s")
            event = msg.get("t")

            if seq:
                self.sequence = seq

            if op != OPCODE.DISPATCH:
                asyncio.ensure_future(self.dispatch_opcode(data, op))
                continue
            else:
                asyncio.ensure_future(self.dispatch_event(data, seq, event))
                continue

        await self.close()

    async def dispatch_opcode(self, data, op):
        if op == OPCODE.HELLO:
            if self._keep_alive:
                self._keep_alive.stop()
            self._keep_alive = BeeGees(ws=self, interval=data["heartbeat_interval"] / 1000)
            # as per API, we shouldn't send a heartbeat on connect, wait a random offset
            self.loop.call_later(self._keep_alive.interval * random.uniform(0, 0.5), self._keep_alive.start)
            if not self.session_id:
                return await self.identify()
            return await self.resume_connection()
        elif op == OPCODE.HEARTBEAT_ACK:
            return self._keep_alive.ack()
        elif op == OPCODE.HEARTBEAT:
            return await self.send_heartbeat()
        elif op == OPCODE.RECONNECT:
            log.info("Gateway requested reconnect. Reconnecting...")
            return await self.close(resume=True)
        elif op == OPCODE.INVALIDATE_SESSION:
            log.warning("Gateway has invalidated session! Reconnecting...")
            return await self.close()
        else:
            return log.debug(f"Unhandled OPCODE: {op} = {OPCODE(op).name}")

    async def dispatch_event(self, data, seq, event):
        if event == "READY":
            self._trace = data.get("_trace", [])
            self.sequence = seq
            self.session_id = data["session_id"]
            log.debug(f"Successfully connected to Gateway! Trace: {self._trace} Session_ID: {self.session_id}")
            self._dispatch_soon(WebsocketReady(data))
        elif event == "RESUMED":
            log.debug(f"Successfully resumed connection! Session_ID: {self.session_id}")
            self._dispatch_soon(events.Resume())

        elif event == "GUILD_MEMBERS_CHUNK":
            # this *could* take ages to return, do **not** wait for it
            return asyncio.ensure_future(self._process_member_chunk(data))
        else:
            event_name = f"raw_{event.lower()}"
            processor = self.client.processors.get(event_name)
            if processor:
                try:
                    asyncio.ensure_future(processor(RawGatewayEvent(data)))
                except Exception as ex:
                    log.error(f"Failed to run event processor for {event_name}: {ex}")
            else:
                log.warning(f"No processor for `{event_name}`")
        self._dispatch_soon(RawGatewayEvent(data, override_name="raw_socket_receive"))

    def _dispatch_soon(self, event: BaseEvent):
        self.loop.call_soon(self.client.dispatch, event)

    def __del__(self) -> None:
        if not self.closed.is_set():
            self.loop.run_until_complete(self.close())

    async def close(self, code: int = None, *, shutdown: bool = False, resume: bool = False) -> None:
        """
        Close the connection to the gateway.

        Parameters:
            code: the close code to use
            resume: You are intending to resume this connection
            shutdown: You are shutting down the bot completely
        """
        self.closed.set()
        self.resume = resume
        self.shutdown = shutdown

        if shutdown and not code:
            code = 1000
        if resume and not code:
            code = 1012

        await self.ws.close(code=code)
        if isinstance(self._keep_alive, BeeGees):
            self._keep_alive.stop()

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

    async def resume_connection(self) -> None:
        """Send a resume payload to the gateway."""
        payload = {
            "op": OPCODE.RESUME,
            "d": {"token": self.client.http.token, "seq": self.sequence, "session_id": self.session_id},
        }
        await self.send_json(payload)
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
        guild = self.client.cache.guild_cache.get(g_id)

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
                self.client.cache.place_member_data(g_id, member)
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
