import asyncio
import logging
import traceback
from datetime import datetime
from typing import TYPE_CHECKING, Optional, Union

from dis_snek.models.discord.enums import Intents, Status, ActivityType
from dis_snek.models.discord.activity import Activity
from dis_snek.client.errors import SnakeException, WebSocketClosed
from dis_snek.client.const import logger_name, MISSING, Absent
from dis_snek.client.utils.attr_utils import define
from .gateway import WebsocketClient, GatewayClient
from dis_snek.api import events
from ...models.snek.VoiceState import ActiveVoiceState

if TYPE_CHECKING:
    from dis_snek import Snake, Snowflake_Type

__all__ = ["ConnectionState"]

log = logging.getLogger(logger_name)


@define(kw_only=False)
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

    gateway_started: asyncio.Event = asyncio.Event()
    """Event to check if the gateway has been started."""

    _shard_task: asyncio.Task | None = None

    @property
    def latency(self) -> float:
        """Returns the latency of the websocket connection."""
        return self.gateway.average_latency

    @property
    def average_latency(self) -> float:
        """Returns the average latency of the websocket connection."""
        return self.gateway.average_latency

    @property
    def presence(self) -> dict:
        return {
            "status": self.client._status,
            "activities": [self.client._activity.to_dict()] if self.client._activity else [],
        }

    async def start(self) -> None:
        """Connect to the Discord Gateway."""
        self.gateway_url = await self.client.http.get_gateway()

        log.debug(f"Starting Shard ID {self.shard_id}")
        self.start_time = datetime.now()
        self._shard_task = asyncio.create_task(self._ws_connect())

        self.gateway_started.set()

        # Historically this method didn't return until the connection closed
        # so we need to wait for the task to exit.
        await self._shard_task

    async def stop(self) -> None:
        """Disconnect from the Discord Gateway."""
        log.debug(f"Shutting down shard ID {self.shard_id}")
        if self.gateway is not None:
            self.gateway.close()
            self.gateway = None

        if self._shard_task is not None:
            await self._shard_task
            self._shard_task = None

        self.gateway_started.clear()

    async def _ws_connect(self) -> None:
        log.info("Attempting to initially connect to gateway...")
        try:
            async with GatewayClient(self, (self.shard_id, self.client.total_shards)) as self.gateway:
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
        self, status: Optional[Union[str, Status]] = Status.ONLINE, activity: Absent[Union[Activity, str]] = MISSING
    ) -> None:
        """
        Change the bots presence.

        Args:
            status: The status for the bot to be. i.e. online, afk, etc.
            activity: The activity for the bot to be displayed as doing.

        note::
            Bots may only be `playing` `streaming` `listening` `watching` or `competing`, other activity types are likely to fail.

        """
        if activity is not MISSING:
            if activity is None:
                activity = []
            else:
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
            activity = self.client.activity

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

    def get_voice_state(self, guild_id: "Snowflake_Type") -> Optional[ActiveVoiceState]:
        return self.client.cache.get_bot_voice_state(guild_id)

    async def voice_connect(self, guild_id, channel_id) -> ActiveVoiceState:
        voice_state = ActiveVoiceState(client=self.client, guild_id=guild_id, channel_id=channel_id)
        await voice_state.connect()
        self.client.cache.place_bot_voice_state(voice_state)
        return voice_state
