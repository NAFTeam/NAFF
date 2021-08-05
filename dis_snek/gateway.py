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
import concurrent.futures
import logging
import sys
import threading
import time
import zlib
from typing import (
    Any,
    Callable,
    Coroutine,
    List,
    Optional
)

import orjson
from aiohttp import WSMsgType

from dis_snek.const import logger_name
from dis_snek.errors import WebSocketClosed, WebSocketRestart
from dis_snek.http_client import HTTPClient, DiscordClientWebSocketResponse
from dis_snek.models.enums import Intents, WebSocketOPCodes as OPCODE

log = logging.getLogger(logger_name)


class BeeGees(threading.Thread):
    """
    Keeps the gateway alive.

    ♫ Stayin' Alive ♫

    :param ws: WebsocketClient
    :param interval: How often to send heartbeats -- dictated by discord
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

        :return: dict representing heartbeat
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

    :param session_id: The session_id to use, if resuming
    :param sequence: The sequence to use, if resuming
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
        self._keep_alive = None

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
    ):
        """
        Connect to the discord gateway.

        :param http: The HTTPClient
        :param dispatch: A method to dispatch events
        :param intents: The intents of this bot
        :param resume: Are we attempting to resume?
        :param session_id: The session id to use, if resuming
        :param sequence: The sequence to use, if resuming
        :return:
        """
        cls.http = http
        cls._gateway = await http.get_gateway()
        cls.intents = intents
        cls.dispatch = dispatch
        cls.ws = await cls.http.websock_connect(cls._gateway)
        dispatch("connect")
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

        if type(resp.data) is bytes:
            self.buffer.extend(msg)

            if len(msg) < 4 or msg[-4:] != b"\x00\x00\xff\xff":
                # message isnt complete yet, wait
                return

            msg = self._zlib.decompress(self.buffer)
            self.buffer = bytearray()

            msg = msg.decode("utf-8")

        if resp.type == WSMsgType.CLOSE:
            await self.close(msg)
            raise WebSocketClosed(msg)

        msg = orjson.loads(msg)
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
                self.dispatch("websocket_ready", data)
                return
            else:
                self.dispatch("raw_socket_receive", msg)
            self.dispatch(f"raw_{msg.get('t').lower()}", data)

    async def run(self) -> None:
        """Start receiving events from the websocket."""
        while not self._closed:
            await self._receive()

    def __del__(self) -> None:
        if not self._closed:
            self.http.loop.run_until_complete(self.close())

    async def close(self, code: int = 1000) -> None:
        """
        Close the connection to the gateway.

        :param code: the close code to use
        :return:
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

        :param data: The data to send
        """
        await self.ws.send_str(data)

    async def send_json(self, data: dict) -> None:
        """
        Send json data to the gateway.

        :param data: The data to send
        """
        await self.send(orjson.dumps(data).decode("utf-8"))

    async def identify(self) -> None:
        """Send an identify payload to the gateway."""
        data = {
            "op": OPCODE.IDENTIFY,
            "d": {
                "token": self.http.token,
                "intents": self.intents,
                "large_threshold": 250,
                "properties": {"$os": sys.platform, "$browser": "dis.snek", "$device": "dis.snek"},
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
        self.dispatch("resume")
        log.debug("Client is attempting to resume a connection")

    async def send_heartbeat(self, data: dict) -> None:
        """Send a heartbeat to the gateway."""
        await self.send_json(data)
