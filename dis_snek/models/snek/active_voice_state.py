import asyncio
import logging
from typing import Optional

from discord_typings import VoiceStateData

from dis_snek.api.voice.audio import BaseAudio, AudioVolume
from dis_snek.api.voice.player import Player
from dis_snek.api.voice.voice_gateway import VoiceGateway
from dis_snek.client.const import logger_name, MISSING
from dis_snek.client.errors import SnakeException, VoiceAlreadyConnected, VoiceConnectionTimeout
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
        """The current audio being played"""
        if self.player:
            return self.player.current_audio

    @property
    def volume(self) -> float:
        """Get the volume of the player"""
        return self._volume

    @volume.setter
    def volume(self, value) -> None:
        """Set the volume of the player"""
        if value < 0.0:
            raise ValueError("Volume may not be negative.")
        self._volume = value
        if self.player and isinstance(self.player.current_audio, AudioVolume):
            self.player.current_audio.volume = value

    @property
    def paused(self) -> bool:
        """Is the player currently paused"""
        return self.player.paused

    @property
    def playing(self) -> bool:
        """Are we currently playing something?"""
        # noinspection PyProtectedMember
        if not self.player or not self.current_audio or self.player.stopped or not self.player._resume.is_set():
            # if any of the above are truthy, we aren't playing
            return False
        return True

    @property
    def stopped(self) -> bool:
        """Is the player stopped?"""
        if self.player:
            return self.player.stopped
        return True

    @property
    def connected(self) -> bool:
        """Is this voice state currently connected?"""
        # noinspection PyProtectedMember
        if self.ws is None:
            return False
        return self.ws._closed.is_set()

    async def wait_for_stopped(self) -> None:
        """Wait for the player to stop playing."""
        if self.player:
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

    async def connect(self, timeout: int = 5) -> None:
        """Establish the voice connection."""
        if self.connected:
            raise VoiceAlreadyConnected

        def predicate(event) -> bool:
            return int(event.data["guild_id"]) == self._guild_id

        await self._client.ws.voice_state_update(self._guild_id, self._channel_id, self.self_mute, self.self_deaf)

        log.debug("Waiting for voice connection data...")

        try:
            self._voice_state, self._voice_server = await asyncio.gather(
                self._client.wait_for("raw_voice_state_update", predicate, timeout=timeout),
                self._client.wait_for("raw_voice_server_update", predicate, timeout=timeout),
            )
        except asyncio.TimeoutError:
            raise VoiceConnectionTimeout from None

        log.debug("Attempting to initialise voice gateway...")
        await self.ws_connect()

    async def disconnect(self) -> None:
        """Disconnect from the voice channel."""
        await self._client.ws.voice_state_update(self._guild_id, None)

    async def move(self, channel: "Snowflake_Type") -> None:
        """
        Move to another voice channel.

        Args:
            channel: The channel to move to
        """
        target_channel = to_snowflake(channel)
        if target_channel != self._channel_id:
            self.ws.close()
            self._channel_id = target_channel
            await self.connect()

    async def stop(self) -> None:
        """Stop playback."""
        self.player.stop()
        await self.player._stopped.wait()

    def pause(self) -> None:
        """Pause playback"""
        self.player.pause()

    def resume(self) -> None:
        """Resume playback."""
        self.player.resume()

    async def play(self, audio: BaseAudio) -> None:
        """
        Start playing an audio object.

        Waits for the player to stop before returning.

        Args:
            audio: The audio object to play
        """
        if self.player:
            await self.stop()

        self.player = Player(audio, self, asyncio.get_running_loop())

        with Player(audio, self, asyncio.get_running_loop()) as self.player:
            self.player.play()
            await self.wait_for_stopped()

    def play_no_wait(self, audio: BaseAudio) -> None:
        """
        Start playing an audio object, but don't wait for playback to finish.

        Args:
            audio: The audio object to play
        """
        asyncio.create_task(self.play(audio))

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
            log.info(f"Disconnecting from voice channel {self._channel_id}")
            await self._close_connection()
            self._client.cache.delete_bot_voice_state(self._guild_id)
            return

        self.update_from_dict(data)

    async def _close_connection(self) -> None:
        if self.playing:
            await self.stop()
        if self.connected:
            self.ws.close()
