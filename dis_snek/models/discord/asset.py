from typing import TYPE_CHECKING, Optional, Union

from dis_snek.client.utils.attr_utils import define, field
from dis_snek.client.utils.serializer import no_export_meta

if TYPE_CHECKING:
    from os import PathLike

    from dis_snek.client import Snake

__all__ = ["Asset"]


@define(kw_only=False)
class Asset:
    """
    Represents a discord asset.

    Attributes:
        BASE str: The `cdn` address for assets
        url str: The URL of this asset
        hash Optional[str]: The hash of this asset

    """

    BASE = "https://cdn.discordapp.com"

    _client: "Snake" = field(metadata=no_export_meta)
    _url: str = field(repr=True)
    hash: Optional[str] = field(repr=True, default=None)

    @classmethod
    def from_path_hash(cls, client: "Snake", path: str, asset_hash: str) -> "Asset":
        url = f"{cls.BASE}/{path.format(asset_hash)}"
        return cls(client=client, url=url, hash=asset_hash)

    @property
    def url(self) -> str:
        ext = ".gif" if self.animated else ".png"
        return f"{self._url}{ext}?size=4096"

    @property
    def animated(self) -> bool:
        """True if this asset is animated."""
        return bool(self.hash) and self.hash.startswith("a_")

    async def fetch(self, extension: Optional[str] = None, size: Optional[int] = None) -> bytes:
        """
        Fetch the asset from the Discord CDN.

        Args:
            extension: File extension
            size: File size

        Returns:
            Raw byte array of the file

        Raises:
            ValueError: Incorrect file size if not power of 2 between 16 and 4096

        """
        if not extension:
            extension = ".gif" if self.animated else ".png"

        url = self._url + extension

        if size:
            if not ((size != 0) and (size & (size - 1) == 0)):  # if not power of 2
                raise ValueError("Size should be a power of 2")
            if not 16 <= size <= 4096:
                raise ValueError("Size should be between 16 and 4096")

            url = f"{url}?size={size}"

        return await self._client.http.request_cdn(url, self)

    async def save(
        self, fd: Union[str, bytes, "PathLike", int], extension: Optional[str] = None, size: Optional[int] = None
    ) -> int:
        """
        Save the asset to a file.

        Args:
            fd: File destination
            extention: File extension
            size: File size

        Return:
            Status code

        """
        content = await self.fetch(extension=extension, size=size)
        with open(fd, "wb") as f:
            return f.write(content)
