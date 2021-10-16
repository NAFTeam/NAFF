"""
This file outlines the interaction between snek and Discord's Gateway API.
"""
import asyncio
import concurrent.futures
import logging
import sys
import threading
import time
import zlib
from typing import Any, Callable, Coroutine, List, Optional

from aiohttp import WSMsgType

from dis_snek.const import logger_name, MISSING
from dis_snek.errors import WebSocketClosed, WebSocketRestart
from dis_snek.http_client import DiscordClientWebSocketResponse, HTTPClient
from dis_snek.models import events
from dis_snek.models.enums import Intents, Status
from dis_snek.models.enums import WebSocketOPCodes as OPCODE
from dis_snek.utils.input_utils import OverriddenJson
from dis_snek.utils.serializer import dict_filter_none

log = logging.getLogger(logger_name)


class BeeGees(threading.Thread):
    """
    Keeps the gateway connection alive.

    ♫ Stayin' Alive ♫

    Parameters:
        ws WebsocketClient: WebsocketClient
        interval int: How often to send heartbeats -- dictated by discord

    Attributes:
        behind_msg: The log message used when the heartbeat is late
        block_msg: The log message used when the heartbeat is blocked
        msg: The log message used when a hearbeat is sent
        last_recv: When the last heartbeat was received
    """

    ws: Any  # actually WebsocketClient, but these 2 classes reference each other so ¯\_(ツ)_/¯
    _main_thread_id: int
    _interval: int
    daemon: bool
    msg: str
    block_msg: str
    behind_msg: str
    _stop_ev: threading.Event
    _last_ack: float
    _last_send: float
    last_recv: float
    heartbeat_timeout: int

    def __init__(self, ws: Any, interval: int) -> None:
        self.ws = ws
        self._main_thread_id = ws.thread_id
        self.interval = interval
        super().__init__()
        self.daemon = True

        self.msg = "Keeping shard ID %s websocket alive with sequence %s."
        self.block_msg = "Shard ID %s heartbeat blocked for more than %s seconds."
        self.behind_msg = "Can't keep up, shard ID %s websocket is %.1fs behind."

        self._stop_ev = threading.Event()
        self._last_ack = time.perf_counter()
        self._last_send = time.perf_counter()
        self._last_recv = time.perf_counter()
        self.latency = float("inf")
        self.heartbeat_timeout = ws._max_heartbeat_timeout

    def run(self) -> None:
        """Start automatically sending heartbeats to discord."""
        while not self._stop_ev.wait(self.interval):

            data = self.get_payload()
            log.debug(self.msg, 0, data["d"])
            f = asyncio.run_coroutine_threadsafe(self.ws.send_heartbeat(data), loop=self.ws.http.loop)
            duration = 0
            try:
                # block until sending is complete
                while True:
                    try:
                        f.result(10)
                        break
                    except concurrent.futures.TimeoutError:
                        duration += 10
                        log.warning("Heartbeat took too long")
            except Exception:
                log.debug(f"Unable to send heartbeat for {duration} seconds. Closing")
                self.stop()
            else:
                self._last_send = time.perf_counter()

    def get_payload(self) -> dict:
        """
        Get a payload representing a heartbeat.

        returns:
            representation of the heartbeat payload
        """
        return {"op": OPCODE.HEARTBEAT, "d": self.ws.sequence}

    def stop(self) -> None:
        """Stop sending heartbeats."""
        self._stop_ev.set()

    def recv(self) -> None:
        """Log the time that the last heartbeat was received."""
        self._last_recv = time.perf_counter()

    def ack(self) -> None:
        """Log discord ack the heartbeat."""
        ack_time = time.perf_counter()
        self._last_ack = time.perf_counter()
        self.latency = ack_time - self._last_send
        if self.latency > 10:
            log.warning(self.behind_msg, 0, self.latency)


class WebsocketClient:
    """
    Manages the connection to discord's websocket.

    Parameters:
        session_id: The session_id to use, if resuming
        sequence: The sequence to use, if resuming

    Attributes:
        buffer: A buffer to hold incoming data until its complete
        compress: Should the connection be compressed
        intents: The intents used in this connection
        sequence: The sequence of this connection
        session_id: The session ID of this connection
    """

    __slots__ = (
        "http",
        "_gateway",
        "ws",
        "intents",
        "session_id",
        "dispatch",
        "sequence",
        "_keep_alive",
        "_closed",
        "buffer",
        "_zlib",
        "_max_heartbeat_timeout",
        "thread_id",
        "_trace",
    )
    buffer: bytearray
    _closed: bool
    compress: int
    dispatch: Callable[..., Coroutine]
    _gateway: str
    http: HTTPClient
    _keep_alive: Optional[BeeGees]
    _max_heartbeat_timeout: int
    intents: Intents
    sequence: Optional[int]
    session_id: Optional[int]
    thread_id: int
    _trace: List[str]
    ws: DiscordClientWebSocketResponse

    def __init__(self, session_id: Optional[int] = None, sequence: Optional[int] = None) -> None:
        self.session_id = session_id
        self.sequence = sequence

        self.buffer = bytearray()
        self._zlib = zlib.decompressobj()
        self._keep_alive = MISSING

        self._max_heartbeat_timeout = 120
        self.thread_id = threading.get_ident()
        self._trace = []

        self._closed = False

    @classmethod
    async def connect(
        cls,
        http: HTTPClient,
        dispatch: Callable[..., Coroutine],
        intents: Intents,
        resume: bool = False,
        session_id: Optional[int] = None,
        sequence: Optional[int] = None,
        presence: Optional[dict] = None,
    ):
        """
        Connect to the discord gateway.

        parameters:
            http: The HTTPClient
            dispatch: A method to dispatch events
            intents: The intents of this bot
            resume: Are we attempting to resume?
            session_id: The session id to use, if resuming
            sequence: The sequence to use, if resuming
        """
        cls.http = http
        cls._gateway = await http.get_gateway()
        cls.intents = intents
        cls.dispatch = dispatch
        cls.presence = presence
        cls.ws = await cls.http.websocket_connect(cls._gateway)
        dispatch(events.Connect())
        if resume:
            return cls(session_id, sequence)
        return cls()

    @property
    def latency(self) -> float:
        """Get the latency of the connection."""
        return float("inf") if not self._keep_alive else self._keep_alive.latency

    async def _receive(self) -> None:
        resp = await self.ws.receive()
        msg = resp.data

        if isinstance(resp.data, bytes):
            self.buffer.extend(msg)

            if len(msg) < 4 or msg[-4:] != b"\x00\x00\xff\xff":
                # message isnt complete yet, wait
                return

            msg = self._zlib.decompress(self.buffer)
            self.buffer = bytearray()

            msg = msg.decode("utf-8")

        if resp.type == WSMsgType.CLOSE:
            log.debug(f"Disconnecting from gateway! Reason: {resp.data}::{resp.extra}")
            await self.close(msg)
            return

        if resp.type == WSMsgType.CLOSING:
            return

        if resp.type == WSMsgType.CLOSED:
            raise WebSocketClosed(1000)

        msg = OverriddenJson.loads(msg)
        log.debug(f"Websocket Event: {msg}")

        op = msg.get("op")
        data = msg.get("d")
        seq = msg.get("s")
        if seq is not None:
            self.sequence = seq

        if op != OPCODE.DISPATCH:
            if op == OPCODE.HELLO:
                interval = data["heartbeat_interval"] / 1000
                self._keep_alive = BeeGees(ws=self, interval=interval)
                await self.send_json(self._keep_alive.get_payload())
                self._keep_alive.start()
                if not self.session_id:
                    await self.identify()
                else:
                    await self.resume()
                return

            if op == OPCODE.HEARTBEAT:
                if self._keep_alive:
                    await self.send_json(self._keep_alive.get_payload())
                return
            if op == OPCODE.HEARTBEAT_ACK:
                if self._keep_alive:
                    self._keep_alive.ack()
                return

            if op in (OPCODE.INVALIDATE_SESSION, OPCODE.RECONNECT):
                # session invalidated, restart
                log.debug(f"Reconnecting to discord due to opcode {op}::{OPCODE(op).name}")
                if data is True or op == OPCODE.RECONNECT:
                    await self.close()
                    raise WebSocketRestart(True)

                self.session_id = self.sequence = None
                log.warning("Session has been invalidated")

                await self.close(code=1000)
                raise WebSocketRestart

        else:
            if msg.get("t") == "READY":
                self._trace = data.get("_trace", [])
                self.sequence = msg["s"]
                self.session_id = data["session_id"]
                log.info(f"Successfully connected to Gateway! Trace: {self._trace} Session_ID: {self.session_id}")
                self.dispatch(events.RawGatewayEvent(data, override_name="websocket_ready"))
                return
            else:
                self.dispatch(events.RawGatewayEvent(msg, override_name="raw_socket_receive"))
            self.dispatch(events.RawGatewayEvent(data, override_name=f"raw_{msg.get('t').lower()}"))

    async def run(self) -> None:
        """Start receiving events from the websocket."""
        while not self._closed:
            await self._receive()
        print("Closed")

    def __del__(self) -> None:
        if not self._closed:
            self.http.loop.run_until_complete(self.close())

    async def close(self, code: int = 1000) -> None:
        """
        Close the connection to the gateway.

        Parameters:
            code: the close code to use
        """
        if self._closed:
            return
        await self.ws.close(code=code)
        if isinstance(self._keep_alive, BeeGees):
            self._keep_alive.stop()
        self._closed = True

    async def send(self, data: str) -> None:
        """
        Send data to the gateway.

        Parameters:
            data: The data to send
        """
        await self.ws.send_str(data)

    async def send_json(self, data: dict) -> None:
        """
        Send json data to the gateway.

        Parameters:
            data: The data to send
        """
        data = OverriddenJson.dumps(data)
        log.debug(f"Sending data to gateway: {data}")
        await self.send(data)

    async def identify(self) -> None:
        """Send an identify payload to the gateway."""
        data = {
            "op": OPCODE.IDENTIFY,
            "d": {
                "token": self.http.token,
                "intents": self.intents,
                "large_threshold": 250,
                "properties": {"$os": sys.platform, "$browser": "dis.snek", "$device": "dis.snek"},
                "presence": self.presence,
            },
            "compress": True,
        }
        await self.send_json(data)
        log.debug(f"Client has identified itself to Gateway, requesting intents: {self.intents}!")

    async def resume(self) -> None:
        """Send a resume payload to the gateway."""
        data = {
            "op": OPCODE.RESUME,
            "d": {"token": self.http.token, "seq": self.sequence, "session_id": self.session_id},
        }
        await self.send_json(data)
        self.dispatch(events.Resume())
        log.debug("Client is attempting to resume a connection")

    async def send_heartbeat(self, data: dict) -> None:
        """Send a heartbeat to the gateway."""
        await self.send_json(data)

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
