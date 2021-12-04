from typing import TYPE_CHECKING, Optional, Union

import attr

from dis_snek.utils.serializer import no_export_meta

if TYPE_CHECKING:
    from os import PathLike

    from dis_snek.client import Snake


@attr.s(slots=True)
class Asset:
    """
    Represents a discord asset.

    Attributes:
        BASE str: The `cdn` address for assets
        url str: The URL of this asset
        hash Optional[str]: The hash of this asset
    """

    BASE = "https://cdn.discordapp.com"

    _client: "Snake" = attr.field(metadata=no_export_meta)
    _url: str = attr.field()
    hash: Optional[str] = attr.field(default=None)

    @classmethod
    def from_path_hash(cls, client: "Snake", path: str, asset_hash: str) -> "Asset":
        url = f"{cls.BASE}/{path.format(asset_hash)}"
        return cls(client=client, url=url, hash=asset_hash)

    @property
    def url(self) -> str:
        return f"{self._url}?size=4096"

    @property
    def animated(self) -> bool:
        """True if this asset is animated"""
        if not self.hash:
            return None
        return self.hash.startswith("a_")

    async def get(self, extension: Optional[str] = None, size: Optional[int] = None) -> bytes:
        """
        Get the asset from the Discord CDN

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
        self, fd: Union[str, bytes, "PathLike", int], extension: Optional[str] = None, size: Optional[int] = None
    ) -> int:
        """
        Save the asset to a file

        Args:
            fd: File destination
            extention: File extension
            size: File size

        Return:
            Status code
        """
        content = await self.get(extension=extension, size=size)
        with open(fd, "wb") as f:
            return f.write(content)
