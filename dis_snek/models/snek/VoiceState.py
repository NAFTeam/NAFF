import asyncio
import logging
import threading
import time
from asyncio import AbstractEventLoop
from threading import Thread
from typing import Optional

from pip._internal.resolution.resolvelib import factory

from dis_snek.api.voice.audio import BaseAudio, AudioVolume
from dis_snek.api.voice.opus import Encoder
from dis_snek.api.voice.player import Player
from dis_snek.api.voice.voice_gateway import VoiceGateway
from dis_snek.client.const import logger_name, MISSING
from dis_snek.client.utils import optional
from dis_snek.client.utils.attr_utils import define, field
from dis_snek.models.discord.snowflake import Snowflake_Type, SnowflakeObject, to_snowflake
from dis_snek.models.discord.voice_state import VoiceState

log = logging.getLogger(logger_name)


@define()
class ActiveVoiceState(VoiceState):
    ws: Optional[VoiceGateway] = field(default=None)
    """The websocket for this voice state"""
    player: Optional[Player] = field(default=None)
    """The playback task that broadcasts audio data to discord"""
    _volume: float = 0.5

    # standard voice states expect this data, this voice state lacks it initially; so we make them optional
    user_id: "Snowflake_Type" = field(default=MISSING, converter=optional(to_snowflake))
    _guild_id: Optional["Snowflake_Type"] = field(default=None, converter=optional(to_snowflake))
    _member_id: Optional["Snowflake_Type"] = field(default=None, converter=optional(to_snowflake))

    def __attrs_post_init__(self):
        # jank line to handle the two inherently incompatible data structures
        self._member_id = self.user_id = self._client.user.id

    def __del__(self):
        asyncio.create_task(self.disconnect())
        self.player.stop()

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
        if not self.current_audio or self.player.stopped or self.player.resume.is_set():
            return False
        return True

    @property
    def stopped(self) -> bool:
        return self.player.stopped

    async def _ws_connect(self) -> None:
        async with self.ws:
            try:
                await self.ws.run()
            finally:
                if self._playing:
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
        self._resume.clear()

    def resume(self) -> None:
        self._resume.set()

    async def play(self, audio: BaseAudio) -> None:
        if self.player:
            await self.stop()

        self.player = Player(audio, self, asyncio.get_running_loop())

        self.player.play()

    async def update_voice_server(self, data) -> None:
        self.ws.set_new_voice_server(data)
