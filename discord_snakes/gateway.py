import asyncio
import concurrent.futures
import logging
import sys
import threading
import time
import traceback
import zlib
from typing import Optional

import orjson
from aiohttp import WSMsgType

from discord_snakes.const import logger_name
from discord_snakes.errors import BadRequest, SnakeException
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
            try:
                # block until sending is complete
                total = 0
                while True:
                    try:
                        f.result(10)
                        break
                    except concurrent.futures.TimeoutError:
                        total += 10
                        log.warning("Heartbeat took too l")
            except Exception:
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
        "_zlib",
        "_max_heartbeat_timeout",
        "thread_id",
        "_trace",
    )

    def __init__(self):
        self.event_handler = None
        self.intents = None

        self.auto_reconnect = None
        self.session_id = None
        self._zlib = zlib.decompressobj()

        self.sequence = None
        self._keep_alive: Optional[BeeGees] = None
        self._max_heartbeat_timeout = 120
        self.thread_id = threading.get_ident()
        self._trace = []

        self._closed = False

    @classmethod
    async def connect(cls, http, dispatch):
        cls.http = http
        cls._gateway = await http.get_gateway()
        cls.ws = await cls.http.websock_connect(cls._gateway)
        cls.dispatch = dispatch
        return cls()

    @property
    def latency(self) -> float:
        return float("inf") if not self._keep_alive else self._keep_alive.latency

    def close_reason(self, code):
        """Client was disconnected, print the reason"""
        dat = {
            "1000": "Normal Closure",
            "4000": "We're not sure what went wrong. Try reconnecting?",
            "4001": "You sent an invalid Gateway opcode or an invalid payload for an opcode. Don't do that!",
            "4002": "You sent an invalid payload to us. Don't do that!",
            "4003": "You sent us a payload prior to identifying.",
            "4004": "The account token sent with your identify payload is incorrect.",
            "4005": "You sent more than one identify payload. Don't do that!",
            "4007": "The sequence sent when resuming the session was invalid. Reconnect and start a new session.",
            "4008": "Woah nelly! You're sending payloads to us too quickly. Slow it down! You will be disconnected on receiving this.",
            "4009": "Your session timed out. Reconnect and start a new one.",
            "4010": "You sent us an invalid shard when identifying.",
            "4011": "The session would have handled too many guilds - you are required to shard your connection in order to connect.",
            "4012": "You sent an invalid version for the gateway.",
            "4013": "You sent an invalid intent for a Gateway Intent. You may have incorrectly calculated the bitwise value.",
            "4014": "You sent a disallowed intent for a Gateway Intent. You may have tried to specify an intent that you have not enabled or are not approved for.",
        }
        return dat[str(code)]

    async def receive(self):
        resp = await self.ws.receive()
        msg = resp.data

        if type(resp.data) is bytes:
            msg = self._zlib.decompress(msg)
            msg = msg.decode("utf-8")

        if resp.type == WSMsgType.CLOSE:
            log.error(self.close_reason(msg))

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
                await self.identify()
                return

            if op == OPCODE.HEARTBEAT:
                if self._keep_alive:
                    await self.send_json(self._keep_alive.get_payload())
                return
            if op == OPCODE.HEARTBEAT_ACK:
                if self._keep_alive:
                    self._keep_alive.ack()
                return

            if op in (OPCODE.RECONNECT, OPCODE.INVALIDATE_SESSION):
                await self.close()
                # todo: reconnection / resume logic
                if op == OPCODE.RECONNECT:
                    log.debug("Requested to reconnect")
                else:
                    log.debug("Session invalid, reconnect required")
                return
        else:
            event = msg.get("t")

            if event == "READY":
                self._trace = data.get("_trace", [])
                self.sequence = msg["s"]
                self.session_id = data["session_id"]
                log.info(f"Successfully connected to Gateway! Trace: {self._trace} Session_ID: {self.session_id}")
            self.dispatch(event.lower())

    async def run(self):
        while not self._closed:
            resp = await self.receive()

    def __del__(self):
        if not self._closed:
            self.http.loop.run_until_complete(self.close())

    async def close(self, code: int = 1000):
        if self._closed:
            return
        await self.ws.close(code=code)
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
                "intents": 513,
                "large_threshold": 250,
                "properties": {"$os": sys.platform, "$browser": "discord.snakes", "$device": "discord.snakes"},
            },
            "compress": True,
        }
        await self.send_json(data)
        log.debug("Client has identified itself to Gateway!")

    async def send_heartbeat(self, data):
        await self.send_json(data)
