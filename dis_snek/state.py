import asyncio
import logging
import traceback
from datetime import datetime
from typing import TYPE_CHECKING, Optional, Union

import aiohttp
import attr

from dis_snek.models.enums import Intents, Status, ActivityType
from dis_snek.models.discord_objects.activity import Activity
from dis_snek.errors import SnakeException, WebSocketClosed, GatewayNotFound
from dis_snek.const import logger_name, MISSING, Absent
from dis_snek.gateway import WebsocketClient
from dis_snek.models import events

if TYPE_CHECKING:
    from dis_snek import Snake

log = logging.getLogger(logger_name)


@attr.s(auto_attribs=True)
class ConnectionState:
    client: "Snake"
    """The bot's client"""
    intents: Intents
    """The event intents in use"""
    shard_id: int
    """The shard ID of this state"""

    gateway: Absent[WebsocketClient] = MISSING
    """The websocket connection for the Discord Gateway."""

    start_time: Absent[datetime] = MISSING
    """The DateTime the bot started at"""

    gateway_url: str = MISSING
    """The URL that the gateway should connect to."""

    _shard_task: asyncio.Task | None = None

    @property
    def latency(self) -> float:
        """Returns the latency of the websocket connection"""
        return self.gateway.average_latency

    @property
    def average_latency(self) -> float:
        """Returns the average latency of the websocket connection"""
        return self.gateway.average_latency

    @property
    def presence(self) -> dict:
        return {
            "status": self.client._status,
            "activities": [self.client._activity.to_dict()] if self.client._activity else [],
        }

    async def start(self) -> None:
        """Connect to the Discord Gateway"""
        self.gateway_url = await self.client.http.get_gateway()

        log.debug(f"Starting Shard ID {self.shard_id}")
        self.start_time = datetime.now()
        self._shard_task = asyncio.create_task(self._ws_connect())

        # Historically this method didn't return until the connection closed
        # so we need to wait for the task to exit.
        await self._shard_task

    async def stop(self) -> None:
        log.debug(f"Shutting down shard ID {self.shard_id}")
        self._shard_task.cancel()

    async def _ws_connect(self) -> None:
        log.info("Attempting to initially connect to gateway...")
        try:
            async with WebsocketClient(self, (self.shard_id, self.client.total_shards)) as self.gateway:
                try:
                    await self.gateway.run()
                finally:
                    self.client.dispatch(events.Disconnect())

        except WebSocketClosed as ex:
            if ex.code == 4011:
                raise SnakeException("Your bot is too large, you must use shards") from None
            elif ex.code == 4013:
                raise SnakeException(f"Invalid Intents have been passed: {self.intents}") from None
            elif ex.code == 4014:
                raise SnakeException(
                    "You have requested privileged intents that have not been enabled or approved. Check the developer dashboard"
                ) from None
            raise

        except Exception as e:
            self.client.dispatch(events.Disconnect())
            log.error("".join(traceback.format_exception(type(e), e, e.__traceback__)))

    async def change_presence(
        self, status: Optional[Union[str, Status]] = Status.ONLINE, activity: Optional[Union[Activity, str]] = None
    ):
        """
        Change the bots presence.

        Args:
            status: The status for the bot to be. i.e. online, afk, etc.
            activity: The activity for the bot to be displayed as doing.

        note::
            Bots may only be `playing` `streaming` `listening` `watching` or `competing`, other activity types are likely to fail.
        """
        if activity:
            if not isinstance(activity, Activity):
                # squash whatever the user passed into an activity
                activity = Activity.create(name=str(activity))

            if activity.type == ActivityType.STREAMING:
                if not activity.url:
                    log.warning("Streaming activity cannot be set without a valid URL attribute")
            elif activity.type not in [
                ActivityType.GAME,
                ActivityType.STREAMING,
                ActivityType.LISTENING,
                ActivityType.WATCHING,
                ActivityType.COMPETING,
            ]:
                log.warning(f"Activity type `{ActivityType(activity.type).name}` may not be enabled for bots")
        else:
            activity = self._activity if self._activity else []

        if status:
            if not isinstance(status, Status):
                try:
                    status = Status[status.upper()]
                except KeyError:
                    raise ValueError(f"`{status}` is not a valid status type. Please use the Status enum") from None
        else:
            # in case the user set status to None
            if self.client.status:
                status = self.client.status
            else:
                log.warning("Status must be set to a valid status type, defaulting to online")
                status = Status.ONLINE

        self.client._status = status
        self.client._activity = activity
        await self.gateway.change_presence(activity.to_dict() if activity else None, status)
