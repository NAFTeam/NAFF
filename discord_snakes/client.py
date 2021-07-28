import asyncio
import logging
from typing import Coroutine, Optional, List, Dict

from discord_snakes.const import logger_name
from discord_snakes.gateway import WebsocketClient
from discord_snakes.http_client import HTTPClient

log = logging.getLogger(logger_name)


class Snake:
    def __init__(self, loop=None):
        self.loop: asyncio.AbstractEventLoop = asyncio.get_event_loop() if loop is None else loop

        # "Factories"
        self.http: HTTPClient = HTTPClient(loop=self.loop)
        self.WSClient = WebsocketClient

        self._connection = None
        self._closed = False
        self._ready: asyncio.Event = asyncio.Event()

        self._listeners: Dict[str, List] = {}

    @property
    def is_closed(self) -> bool:
        return self._closed

    async def login(self, token):
        """
        Login to discord
        :param token: Your bots token
        """
        log.debug(f"Logging in with token: {token}")
        await self.http.login(token.strip())
        dat = await self.WSClient.connect(self.http)
        dat.dispatcher = self.dispatch

        await dat.run()

    async def dispatch(self, event: str, *args, **kwargs):
        log.debug(f"Dispatching event: {event}")

        # todo: improve this

        listeners = self._listeners.get(event)
        if listeners:
            for _listen in listeners:
                try:
                    await _listen(*args, **kwargs)
                except Exception as e:
                    log.error(f"Error running listener: {e}")

    def add_listener(self, coro: Coroutine, event: Optional[str] = None):
        """
        Add a listener for an event, if no event is passed, one is determined
        :param coro: the coroutine to run
        :param event: the event to listen for
        :return:
        """
        if not event:
            event = coro.__name__

        event = event.strip("on_")

        if event not in self._listeners:
            self._listeners[event] = []
        self._listeners[event].append(coro)
