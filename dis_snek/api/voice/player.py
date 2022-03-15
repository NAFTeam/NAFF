import asyncio
import logging
import threading
import time
from asyncio import AbstractEventLoop
from typing import Optional, TYPE_CHECKING

from dis_snek.client.const import logger_name
from dis_snek.api.voice.audio import BaseAudio, AudioVolume
from dis_snek.api.voice.opus import Encoder

if TYPE_CHECKING:
    from dis_snek.models.snek.active_voice_state import ActiveVoiceState
__all__ = ["Player"]

log = logging.getLogger(logger_name)


class Player(threading.Thread):
    def __init__(self, audio, v_state, loop) -> None:
        super().__init__()
        self.daemon = True

        self.current_audio: Optional[BaseAudio] = audio
        self.state: "ActiveVoiceState" = v_state
        self.loop: AbstractEventLoop = loop

        self._encoder: Encoder = Encoder()

        self.resume: threading.Event = threading.Event()

        self._stop_event: threading.Event = threading.Event()
        self._stopped: asyncio.Event = asyncio.Event()

        self._sent_payloads: int = 0

    def stop(self) -> None:
        self._stop_event.set()

    @property
    def stopped(self) -> bool:
        return self._stopped.is_set()

    @property
    def elapsed_time(self) -> float:
        """How many seconds of audio the player has sent."""
        return self._sent_payloads * self._encoder.delay

    def play(self) -> None:
        self._stop_event.clear()
        self.resume.set()
        try:
            self.start()
        finally:
            self.current_audio.cleanup()

    def run(self) -> None:
        loops = 0

        if isinstance(self.current_audio, AudioVolume):
            # noinspection PyProtectedMember
            self.current_audio.volume = self.state._volume

        self._encoder.set_bitrate(getattr(self.current_audio, "bitrate", self.state.channel.bitrate))

        self._stopped.clear()

        asyncio.run_coroutine_threadsafe(self.state.ws.speaking(True), self.loop)
        log.debug(f"Now playing {self.current_audio!r}")
        start = None

        try:
            while not self._stop_event.is_set():
                if not self.state.ws.ready.is_set() or not self.resume.is_set():
                    asyncio.run_coroutine_threadsafe(self.state.ws.speaking(False), self.loop)
                    log.debug("Voice playback has been suspended!")

                    if not self.state.ws.ready.is_set():
                        self.state.ws.ready.wait()
                    if not self.resume.is_set():
                        self.resume.wait()

                    asyncio.run_coroutine_threadsafe(self.state.ws.speaking(), self.loop)
                    log.debug("Voice playback has been resumed!")
                    start = None
                    loops = 0

                if data := self.current_audio.read(self._encoder.frame_size):
                    self.state.ws.send_packet(data, self._encoder, needs_encode=self.current_audio.needs_encode)
                else:
                    if self.current_audio.locked_stream:
                        self.state.ws.send_packet(b"\xF8\xFF\xFE", self._encoder, needs_encode=False)
                    else:
                        break

                if not start:
                    start = time.perf_counter()

                loops += 1
                self._sent_payloads += 1  # used for duration calc
                time.sleep(max(0.0, start + (self._encoder.delay * loops) - time.perf_counter()))
        finally:
            asyncio.run_coroutine_threadsafe(self.state.ws.speaking(False), self.loop)
            self.loop.call_soon_threadsafe(self._stopped.set)
