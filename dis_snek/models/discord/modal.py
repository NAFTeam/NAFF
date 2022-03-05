import functools
import uuid
from enum import IntEnum
from typing import Union, Optional, List

import attrs

from dis_snek.client.const import MISSING
from dis_snek.client.mixins.serialization import DictSerializationMixin
from dis_snek.models.snek.application_commands import CallbackTypes
from dis_snek.models.discord.components import InteractiveComponent, ComponentTypes
from dis_snek.client.utils.attr_utils import define, field, str_validator


class TextStyles(IntEnum):
    SHORT = 1
    PARAGRAPH = 2


@define(kw_only=False)
class InputText(InteractiveComponent):
    type: Union[ComponentTypes, int] = field(
        default=ComponentTypes.INPUT_TEXT, init=False, on_setattr=attrs.setters.frozen
    )

    label: str = field(validator=str_validator)
    style: Union[TextStyles, int] = field()

    custom_id: Optional[str] = field(factory=lambda: str(uuid.uuid4()), validator=str_validator)

    placeholder: Optional[str] = field(default=MISSING, validator=str_validator, kw_only=True)
    value: Optional[str] = field(default=MISSING, validator=str_validator, kw_only=True)

    required: bool = field(default=True, kw_only=True)
    min_length: Optional[int] = field(default=MISSING, kw_only=True)
    max_length: Optional[int] = field(default=MISSING, kw_only=True)


@define(kw_only=False)
class ShortText(InputText):
    style: Union[TextStyles, int] = field(default=TextStyles.SHORT, kw_only=True)


@define(kw_only=False)
class ParagraphText(InputText):
    style: Union[TextStyles, int] = field(default=TextStyles.PARAGRAPH, kw_only=True)


@define(kw_only=False)
class Modal(DictSerializationMixin):
    type: Union[CallbackTypes, int] = field(default=CallbackTypes.MODAL, init=False, on_setattr=attrs.setters.frozen)
    title: str = field(validator=str_validator)
    components: List[InputText] = field()
    custom_id: Optional[str] = field(factory=lambda: str(uuid.uuid4()), validator=str_validator)

    def __attrs_post_init__(self):
        if self.custom_id is MISSING:
            self.custom_id = str(uuid.uuid4())

    def to_dict(self) -> dict:
        data = super().to_dict()
        components = [{"type": ComponentTypes.ACTION_ROW, "components": [c]} for c in data.get("components", [])]
        return {
            "type": data["type"],
            "data": {"custom_id": data["custom_id"], "title": data["title"], "components": components},
        }
