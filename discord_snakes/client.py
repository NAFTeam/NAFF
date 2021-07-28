import asyncio
import logging

from discord_snakes.const import logger_name
from discord_snakes.http_client import HTTPClient
from discord_snakes.gateway import WebsocketClient

log = logging.getLogger(logger_name)


class Snake:
    def __init__(self, loop=None):
        self.loop: asyncio.AbstractEventLoop = asyncio.get_event_loop() if loop is None else loop
        self.http: HTTPClient = HTTPClient(loop=self.loop)

        self._connection = None
        self._closed = False
        self._ready: asyncio.Event = asyncio.Event()

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
        dat = await WebsocketClient.connect(self.http)

        await dat.run()
