from typing import List, Optional

import attr

from dis_snek.models.discord_objects.user import User
from dis_snek.models.enums import StickerFormatTypes, StickerTypes
from dis_snek.models.snowflake import Snowflake, Snowflake_Type
from dis_snek.utils.attr_utils import DictSerializationMixin


@attr.s(slots=True, kw_only=True)
class Sticker(Snowflake, DictSerializationMixin):
    pack_id: Optional[Snowflake_Type] = attr.ib(default=None)
    name: str = attr.ib()
    description: Optional[str] = attr.ib(default=None)
    tags: str = attr.ib()
    type: StickerTypes = attr.ib(converter=StickerTypes)
    format_type: StickerFormatTypes = attr.ib(converter=StickerFormatTypes)
    available: Optional[bool] = attr.ib(default=True)
    guild_id: Optional[Snowflake_Type] = attr.ib(default=None)
    user: Optional[User] = attr.ib(default=None)
    sort_value: Optional[int] = attr.ib(default=None)


@attr.s(slots=True, kw_only=True)
class StickerPack(Snowflake, DictSerializationMixin):
    stickers: List["Sticker"] = attr.ib(factory=list)
    name: str = attr.ib()
    sku_id: Snowflake_Type = attr.ib()
    cover_sticker_id: Optional[Snowflake_Type] = attr.ib(default=None)
    description: str = attr.ib()
    banner_asset_id: Snowflake_Type = attr.ib()
