from enum import IntEnum
from typing import TYPE_CHECKING, List, Optional, Union

from naff.client.const import MISSING, Absent
from naff.client.mixins.nattrs import Field
from naff.client.utils.attr_converters import optional
from naff.client.utils.serializer import dict_filter_none
from naff.models.discord.snowflake import to_snowflake
from .base import DiscordObject

if TYPE_CHECKING:
    from naff.models.discord.guild import Guild
    from naff.models.discord.user import User
    from naff.models.discord.snowflake import Snowflake_Type

__all__ = ("StickerTypes", "StickerFormatTypes", "StickerItem", "Sticker", "StickerPack")


class StickerTypes(IntEnum):
    """Types of sticker."""

    STANDARD = 1
    """An official sticker in a pack, part of Nitro or in a removed purchasable pack."""
    GUILD = 2
    """A sticker uploaded to a Boosted guild for the guild's members."""


class StickerFormatTypes(IntEnum):
    """File formats for stickers."""

    PNG = 1
    APNG = 2
    LOTTIE = 3


class StickerItem(DiscordObject):
    name: str = Field(repr=True)
    """Name of the sticker."""
    format_type: StickerFormatTypes = Field(repr=True, converter=StickerFormatTypes)
    """Type of sticker image format."""


class Sticker(StickerItem):
    """Represents a sticker that can be sent in messages."""

    pack_id: Optional["Snowflake_Type"] = Field(repr=False, default=None, converter=optional(to_snowflake))
    """For standard stickers, id of the pack the sticker is from."""
    description: Optional[str] = Field(repr=False, default=None)
    """Description of the sticker."""
    tags: str = Field(repr=False)
    """autocomplete/suggestion tags for the sticker (max 200 characters)"""
    type: Union[StickerTypes, int] = Field(repr=False, converter=StickerTypes)
    """Type of sticker."""
    available: Optional[bool] = Field(repr=False, default=True)
    """Whether this guild sticker can be used, may be false due to loss of Server Boosts."""
    sort_value: Optional[int] = Field(repr=False, default=None)
    """The standard sticker's sort order within its pack."""

    _user_id: Optional["Snowflake_Type"] = Field(repr=False, default=None, converter=optional(to_snowflake))
    _guild_id: Optional["Snowflake_Type"] = Field(repr=False, default=None, converter=optional(to_snowflake))

    async def fetch_creator(self) -> "User":
        """
        Fetch the user who created this emoji.

        Returns:
            User object

        """
        return await self._client.cache.fetch_user(self._user_id)

    def get_creator(self) -> "User":
        """
        Get the user who created this emoji.

        Returns:
            User object

        """
        return self._client.cache.get_user(self._user_id)

    async def fetch_guild(self) -> "Guild":
        """
        Fetch the guild associated with this emoji.

        Returns:
            Guild object

        """
        return await self._client.cache.fetch_guild(self._guild_id)

    def get_guild(self) -> "Guild":
        """
        Get the guild associated with this emoji.

        Returns:
            Guild object

        """
        return self._client.cache.get_guild(self._guild_id)

    async def edit(
        self,
        *,
        name: Absent[Optional[str]] = MISSING,
        description: Absent[Optional[str]] = MISSING,
        tags: Absent[Optional[str]] = MISSING,
        reason: Absent[Optional[str]] = MISSING,
    ) -> "Sticker":
        """
        Edit a sticker.

        Args:
            name: New name of the sticker
            description: New description of the sticker
            tags: New tags of the sticker
            reason: Reason for the edit

        Returns:
            The updated sticker instance

        """
        if not self._guild_id:
            raise ValueError("You can only edit guild stickers.")

        payload = dict_filter_none({"name": name, "description": description, "tags": tags})
        sticker_data = await self._client.http.modify_guild_sticker(payload, self._guild_id, self.id, reason)
        return self.update_from_dict(sticker_data)

    async def delete(self, reason: Optional[str] = MISSING) -> None:
        """
        Delete a sticker.

        Args:
            reason: Reason for the deletion

        Raises:
            ValueError: If you attempt to delete a non-guild sticker

        """
        if not self._guild_id:
            raise ValueError("You can only delete guild stickers.")

        await self._client.http.delete_guild_sticker(self._guild_id, self.id, reason)


class StickerPack(DiscordObject):
    """Represents a pack of standard stickers."""

    stickers: List["Sticker"] = Field(repr=False, factory=list)
    """The stickers in the pack."""
    name: str = Field(repr=True)
    """Name of the sticker pack."""
    sku_id: "Snowflake_Type" = Field(repr=True)
    """id of the pack's SKU."""
    cover_sticker_id: Optional["Snowflake_Type"] = Field(repr=False, default=None)
    """id of a sticker in the pack which is shown as the pack's icon."""
    description: str = Field(repr=False)
    """Description of the sticker pack."""
    banner_asset_id: "Snowflake_Type" = Field(repr=False)  # TODO CDN Asset
    """id of the sticker pack's banner image."""
