from typing import Optional, Union, TYPE_CHECKING
from os import PathLike
import attr

if TYPE_CHECKING:
    from dis_snek.client import Snake


@attr.s(slots=True)
class Asset:
    BASE = "https://cdn.discordapp.com"
    _client: "Snake" = attr.field()
    url: str = attr.field()
    hash: Optional[str] = attr.field(default=None)

    @classmethod
    def from_path_hash(cls, client: "Snake", path: str, asset_hash: str):
        url = f"{cls.BASE}/{path.format(asset_hash)}"
        return cls(client=client, url=url, hash=asset_hash)

    @property
    def animated(self):
        if not self.hash:
            return None
        return self.hash.startswith("a_")

    async def get(self, extension: Optional[str] = None, size: Optional[int] = None) -> bytes:
        if not extension:
            extension = ".gif" if self.animated else ".png"

        url = self.url

        if size:
            if not ((size != 0) and (size & (size - 1) == 0)):  # if not power of 2
                raise ValueError("Size should be a power of 2")
            if not 16 <= size <= 4096:
                raise ValueError("Size should be between 16 and 4096")

            url = f"{url}?size={size}"

        url = url + extension
        return await self._client.http.request_cdn(url, self)

    async def save(
        self, fd: Union[str, bytes, PathLike, int], extension: Optional[str] = None, size: Optional[int] = None
    ) -> int:
        content = await self.get(extension=extension, size=size)
        with open(fd, "wb") as f:
            return f.write(content)
