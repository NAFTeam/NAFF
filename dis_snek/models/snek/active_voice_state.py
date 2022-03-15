import asyncio
import logging
from typing import Optional

from discord_typings import VoiceStateData

from dis_snek.api.voice.audio import BaseAudio, AudioVolume
from dis_snek.api.voice.player import Player
from dis_snek.api.voice.voice_gateway import VoiceGateway
from dis_snek.client.const import logger_name, MISSING
from dis_snek.client.utils import optional
from dis_snek.client.utils.attr_utils import define, field
from dis_snek.models.discord.snowflake import Snowflake_Type, SnowflakeObject, to_snowflake
from dis_snek.models.discord.voice_state import VoiceState

__all__ = ["ActiveVoiceState"]

log = logging.getLogger(logger_name)


@define()
class ActiveVoiceState(VoiceState):
    ws: Optional[VoiceGateway] = field(default=None)
    """The websocket for this voice state"""
    player: Optional[Player] = field(default=None)
    """The playback task that broadcasts audio data to discord"""
    _volume: float = field(default=0.5)

    # standard voice states expect this data, this voice state lacks it initially; so we make them optional
    user_id: "Snowflake_Type" = field(default=MISSING, converter=optional(to_snowflake))
    _guild_id: Optional["Snowflake_Type"] = field(default=None, converter=optional(to_snowflake))
    _member_id: Optional["Snowflake_Type"] = field(default=None, converter=optional(to_snowflake))

    def __attrs_post_init__(self) -> None:
        # jank line to handle the two inherently incompatible data structures
        self._member_id = self.user_id = self._client.user.id

    def __del__(self) -> None:
        if self.connected:
            self.ws.close()
        if self.player:
            self.player.stop()

    def __repr__(self) -> str:
        return f"<ActiveVoiceState: channel={self.channel} guild={self.guild} volume={self.volume} playing={self.playing} audio={self.current_audio}>"

    @property
    def current_audio(self) -> Optional[BaseAudio]:
        if self.player:
            return self.player.current_audio

    @property
    def volume(self) -> float:
        return self._volume

    @volume.setter
    def volume(self, value) -> None:
        if value < 0.0:
            raise ValueError("Volume may not be negative.")
        self._volume = value
        if isinstance(self.player.current_audio, AudioVolume):
            self.player.current_audio.volume = value

    @property
    def paused(self) -> bool:
        return not self.player.resume.is_set()

    @property
    def playing(self) -> bool:
        if not self.current_audio or self.player.stopped or not self.player.resume.is_set():
            # if any of the above are truthy, we aren't playing
            return False
        return True

    @property
    def stopped(self) -> bool:
        return self.player.stopped

    @property
    def connected(self) -> bool:
        """Is this voice state currently connected?"""
        # noinspection PyProtectedMember
        return not self.ws._closed.is_set()

    async def wait_for_stopped(self) -> None:
        """Wait for the player to stop playing."""
        # noinspection PyProtectedMember
        await self.player._stopped.wait()

    async def _ws_connect(self) -> None:
        async with self.ws:
            try:
                await self.ws.run()
            finally:
                if self.playing:
                    await self.stop()

    async def ws_connect(self) -> None:
        self.ws = VoiceGateway(self._client._connection_state, self._voice_state.data, self._voice_server.data)

        asyncio.create_task(self._ws_connect())
        await self.ws.wait_until_ready()

    async def connect(self) -> None:
        """Establish the voice connection."""

        def predicate(event) -> bool:
            return event.data["guild_id"] == str(self._guild_id)

        await self._client.ws.voice_state_update(self._guild_id, self._channel_id)

        log.debug("Waiting for voice connection data...")

        self._voice_state, self._voice_server = await asyncio.gather(
            self._client.wait_for("raw_voice_state_update", predicate),
            self._client.wait_for("raw_voice_server_update", predicate),
        )
        log.debug("Attempting to initialise voice gateway...")
        await self.ws_connect()

    async def disconnect(self) -> None:
        await self.stop()
        if self.connected:
            self.ws.close()
        await self._client.ws.voice_state_update(self._guild_id, None)

    async def move(self, channel: SnowflakeObject) -> None:
        self.ws.close()
        self._channel_id = to_snowflake(channel)
        await self.connect()

    async def stop(self) -> None:
        self.player.stop()
        await self.player._stopped.wait()

    def pause(self) -> None:
        self.player.resume.clear()

    def resume(self) -> None:
        self.player.resume.set()

    async def play(self, audio: BaseAudio) -> None:
        if self.player:
            await self.stop()

        self.player = Player(audio, self, asyncio.get_running_loop())

        self.player.play()

    async def _voice_server_update(self, data) -> None:
        """
        An internal receiver for voice server events.

        Args:
            data: voice server data
        """
        self.ws.set_new_voice_server(data)

    async def _voice_state_update(
        self, before: Optional[VoiceState], after: Optional[VoiceState], data: Optional[VoiceStateData]
    ) -> None:
        """
        An internal receiver for voice server state events.

        Args:
            before: The previous voice state
            after: The current voice state
            data: Raw data from gateway
        """
        if after is None:
            # bot disconnected
            log.info("Disconnecting from voice channel due to manual disconnection")
            await self.disconnect()
            self._client.cache.delete_bot_voice_state(self._guild_id)
            return

        self.update_from_dict(data)
