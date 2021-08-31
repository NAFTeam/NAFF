from typing import TYPE_CHECKING, List, Optional

import attr
from dis_snek.models.base_object import DiscordObject
from dis_snek.models.enums import StickerFormatTypes, StickerTypes
from dis_snek.utils.attr_utils import define

if TYPE_CHECKING:
    from dis_snek.models.discord_objects.user import User
    from dis_snek.models.snowflake import Snowflake_Type


@attr.s(slots=True)
class PartialSticker(DiscordObject):
    name: str = attr.ib()
    format_type: StickerFormatTypes = attr.ib(converter=StickerFormatTypes)


@define()
class Sticker(PartialSticker):
    pack_id: Optional["Snowflake_Type"] = attr.ib(default=None)
    description: Optional[str] = attr.ib(default=None)
    tags: str = attr.ib()
    type: StickerTypes = attr.ib(converter=StickerTypes)
    available: Optional[bool] = attr.ib(default=True)
    guild_id: Optional["Snowflake_Type"] = attr.ib(default=None)
    user: Optional["User"] = attr.ib(default=None) # TODO user should be cached.
    sort_value: Optional[int] = attr.ib(default=None)


@define()
class StickerPack(DiscordObject):
    stickers: List["Sticker"] = attr.ib(factory=list)
    name: str = attr.ib()
    sku_id: "Snowflake_Type" = attr.ib()
    cover_sticker_id: Optional["Snowflake_Type"] = attr.ib(default=None)
    description: str = attr.ib()
    banner_asset_id: "Snowflake_Type" = attr.ib()
