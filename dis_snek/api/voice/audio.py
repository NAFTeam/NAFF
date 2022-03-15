import asyncio
import audioop
import subprocess  # noqa: S404
import threading
import time
from abc import ABC, abstractmethod
from pathlib import Path
from typing import Union, Optional

from _cffi_backend import buffer
from yt_dlp import YoutubeDL

ytdl = YoutubeDL(
    {
        "format": "bestaudio/best",
        "outtmpl": "%(extractor)s-%(id)s-%(title)s.%(ext)s",
        "restrictfilenames": True,
        "noplaylist": True,
        "nocheckcertificate": True,
        "ignoreerrors": False,
        "logtostderr": False,
        "quiet": True,
        "no_warnings": True,
        "default_search": "auto",
        "source_address": "0.0.0.0",  # noqa: S104
    }
)


class AudioBuffer:
    def __init__(self):
        self._buffer = bytearray()
        self._lock = threading.Lock()
        self.initialised = threading.Event()

    def __len__(self) -> int:
        return len(self._buffer)

    def extend(self, data: bytes) -> None:
        """
        Extend the buffer with additional data.

        Args:
            data: The data to add
        """
        with self._lock:
            self._buffer.extend(data)
        if not self.initialised.is_set():
            self.initialised.set()

    def read(self, total_bytes: int) -> bytearray:
        """
        Read `total_bytes` bytes of audio from the buffer.

        Args:
            total_bytes: Amount of bytes to read.

        Returns:
            Desired amount of bytes
        """
        with self._lock:
            view = memoryview(self._buffer)
            self._buffer = bytearray(view[total_bytes:])
            data = bytearray(view[:total_bytes])
            if 0 < len(data) < total_bytes:
                # pad incomplete frames with 0's
                data.extend(b"\0" * (total_bytes - len(data)))
            return data


class BaseAudio(ABC):
    """Base structure of the audio."""

    locked_stream: bool
    """Prevents the audio task from closing automatically when no data is received."""
    needs_encode: bool
    """Does this audio data need encoding with opus?"""
    bitrate: Optional[int]
    """Optionally specify a specific bitrate to encode this audio data with"""

    def __del__(self):
        self.cleanup()

    def cleanup(self) -> None:
        """A method to optionally cleanup after this object is no longer required."""
        ...

    @abstractmethod
    def read(self, frame_size: int) -> bytes:
        """
        Reads frame_size ms of audio from source.

        returns:
            bytes of audio
        """
        ...


class Audio(BaseAudio):
    """Audio for playing from file or URL."""

    source: str
    """The source ffmpeg should use to play the audio"""
    process: subprocess.Popen
    """The ffmpeg process to use"""
    buffer: AudioBuffer
    """The audio objects buffer to prevent stuttering"""
    buffer_seconds: int
    """How many seconds of audio should be buffered"""
    read_ahead_task: threading.Thread
    """A thread that reads ahead to create the buffer"""
    ffmpeg_args: str
    """Args to pass to ffmpeg"""
    ffmpeg_before_args: str
    """Args to pass to ffmpeg before the source"""

    def __init__(self, src: Union[str, Path]):
        self.source = src
        self.needs_encode = True
        self.locked_stream = False
        self.process: Optional[subprocess.Popen] = None

        self.buffer = AudioBuffer()

        self.buffer_seconds = 3
        self.read_ahead_task = threading.Thread(target=self._read_ahead, daemon=True)

        self.ffmpeg_before_args = ""
        self.ffmpeg_args = ""

    def __repr__(self):
        return f"<{type(self).__name__}: {self.source}>"

    @property
    def _max_buffer_size(self):
        # 1ms of audio * (buffer seconds * 1000)
        return 192 * (self.buffer_seconds * 1000)

    def _create_process(self):
        cmd = (
            f"ffmpeg {self.ffmpeg_before_args} "
            f"-i {self.source} -f s16le -ar 48000 -ac 2 -loglevel warning pipe:1 -vn "
            f"{self.ffmpeg_args}".split()
        )

        self.process = subprocess.Popen(cmd, stdout=subprocess.PIPE, stderr=subprocess.PIPE)  # noqa: S603
        self.read_ahead_task.start()

        # block until some data is in the buffer
        self.buffer.initialised.wait()

    def _read_ahead(self) -> None:
        while self.process:
            if not len(self.buffer) > self._max_buffer_size:
                self.buffer.extend(self.process.stdout.read(3840))
            else:
                time.sleep(0.1)

    def read(self, frame_size: int) -> bytes:
        """
        Reads frame_size bytes of audio from the buffer.

        returns:
            bytes of audio
        """
        if not self.process:
            self._create_process()

        data = self.buffer.read(frame_size)

        if len(data) != frame_size:
            data = b""

        return data

    def cleanup(self) -> None:
        """Cleans up after this audio object."""
        if self.process:
            self.process.kill()


class AudioVolume(Audio):
    """An audio object with volume control"""

    _volume: float
    """The internal volume level of the audio"""

    def __init__(self, src: Union[str, Path], volume: float = 1.0):
        super().__init__(src)
        self._volume = volume

    @property
    def volume(self) -> float:
        return self._volume

    @volume.setter
    def volume(self, value: float) -> None:
        self._volume = max(value, 0.0)

    def read(self, frame_size: int) -> bytes:
        """
        Reads frame_size ms of audio from source.

        returns:
            bytes of audio
        """
        data = super().read(frame_size)
        return audioop.mul(data, 2, self._volume)


class YTDLAudio(AudioVolume):
    """An audio object to play sources supported by YTDLP"""

    def __init__(self, src, volume: float = 1.0):
        super().__init__(src, volume)
        self.entry: Optional[dict] = None

    @classmethod
    async def from_url(cls, url, stream=True):
        """Create this object from a YTDL support url."""
        data = await asyncio.to_thread(lambda: ytdl.extract_info(url, download=not stream))

        if "entries" in data:
            data = data["entries"][0]

        filename = data["url"] if stream else ytdl.prepare_filename(data)

        new_cls = cls(filename)

        if stream:
            new_cls.ffmpeg_before_args = "-reconnect 1 -reconnect_streamed 1 -reconnect_delay_max 5"

        new_cls.entry = data
        return new_cls
