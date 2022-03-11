import asyncio
import audioop


import subprocess  # noqa: S404
from abc import ABC, abstractmethod
from pathlib import Path
from typing import Union, Optional

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

    def __init__(self, src: Union[str, Path]):
        self.source = src
        self.needs_encode = True
        self.locked_stream = False
        self.process: Optional[subprocess.Popen] = None

    def __repr__(self):
        return f"<{type(self).__name__}: {self.source}>"

    def _create_process(self):
        cmd = f"ffmpeg -i {self.source} -f s16le -ar 48000 -ac 2 -loglevel warning pipe:1"
        self.process = subprocess.Popen(cmd.split(), stdout=subprocess.PIPE, stderr=subprocess.PIPE)  # noqa: S603

    def read(self, frame_size: int) -> bytes:
        """
        Reads frame_size ms of audio from source.

        returns:
            bytes of audio
        """
        if not self.process:
            self._create_process()
        data = self.process.stdout.read(frame_size)
        if len(data) != frame_size:
            data = b""
        return data

    def cleanup(self) -> None:
        """Cleans up subprocess."""
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

    @classmethod
    async def from_url(cls, url, stream=True):
        """Create this object from a YTDL support url."""
        data = await asyncio.to_thread(lambda: ytdl.extract_info(url, download=not stream))

        if "entries" in data:
            data = data["entries"][0]

        filename = data["url"] if stream else ytdl.prepare_filename(data)

        return cls(filename)
