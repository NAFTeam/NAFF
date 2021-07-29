import asyncio
import concurrent.futures
import logging
import sys
import threading
import time
import zlib
from typing import Optional

import orjson
from aiohttp import WSMsgType

from discord_snakes.const import logger_name
from discord_snakes.errors import WebSocketClosed, WebSocketRestart
from discord_snakes.models.enums import WebSocketOPCodes as OPCODE

log = logging.getLogger(logger_name)


class BeeGees(threading.Thread):
    def __init__(self, ws, interval):
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

    def get_payload(self):
        return {"op": OPCODE.HEARTBEAT, "d": self.ws.sequence}

    def stop(self):
        self._stop_ev.set()

    def tick(self):
        self._last_recv = time.perf_counter()

    def ack(self):
        ack_time = time.perf_counter()
        self._last_ack = time.perf_counter()
        self.latency = ack_time - self._last_send
        if self.latency > 10:
            log.warning(self.behind_msg, 0, self.latency)


class WebsocketClient:
    __slots__ = (
        "http",
        "_gateway",
        "ws",
        "event_handler",
        "intents",
        "auto_reconnect",
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

    def __init__(self, session_id=None, sequence=None):
        self.event_handler = None

        self.auto_reconnect = None
        self.session_id = session_id
        self.sequence = sequence

        self.buffer = bytearray()
        self._zlib = zlib.decompressobj()

        self.sequence = None
        self._keep_alive: Optional[BeeGees] = None
        self._max_heartbeat_timeout = 120
        self.thread_id = threading.get_ident()
        self._trace = []

        self._closed = False

    @classmethod
    async def connect(cls, http, dispatch, intents, resume=False, session_id=None, sequence=None):
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
        return float("inf") if not self._keep_alive else self._keep_alive.latency

    async def receive(self):
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
            event = msg.get("t")

            if event == "READY":
                self._trace = data.get("_trace", [])
                self.sequence = msg["s"]
                self.session_id = data["session_id"]
                log.info(f"Successfully connected to Gateway! Trace: {self._trace} Session_ID: {self.session_id}")
                self.dispatch("ready")
            if event == "GUILD_CREATE":
                self.dispatch("raw_guild_create", msg["d"])

    async def run(self):
        while not self._closed:
            await self.receive()

    def __del__(self):
        if not self._closed:
            self.http.loop.run_until_complete(self.close())

    async def close(self, code: int = 1000):
        if self._closed:
            return
        await self.ws.close(code=code)
        self._keep_alive.stop()
        self._closed = True

    async def send(self, data):
        log.debug(f"Sent packet to discord: {data}")
        await self.ws.send_str(data)

    async def send_json(self, data):
        await self.send(orjson.dumps(data).decode("utf-8"))

    async def identify(self):
        data = {
            "op": OPCODE.IDENTIFY,
            "d": {
                "token": self.http.token,
                "intents": self.intents,
                "large_threshold": 250,
                "properties": {"$os": sys.platform, "$browser": "discord.snakes", "$device": "discord.snakes"},
            },
            "compress": True,
        }
        await self.send_json(data)
        log.debug(f"Client has identified itself to Gateway, requesting intents: {self.intents}!")

    async def resume(self):
        data = {
            "op": OPCODE.RESUME,
            "d": {"token": self.http.token, "seq": self.sequence, "session_id": self.session_id},
        }
        await self.send_json(data)
        self.dispatch("resume")
        log.debug(f"Client is attempting to resume a connection")

    async def send_heartbeat(self, data):
        await self.send_json(data)
