import functools
import uuid
from enum import IntEnum
from typing import Union, Optional, List

import attr

from dis_snek.client.const import MISSING
from dis_snek.client.mixins.serialization import DictSerializationMixin
from dis_snek.models.snek.application_commands import CallbackTypes
from dis_snek.models.discord.components import InteractiveComponent, ComponentTypes
from dis_snek.client.utils.attr_utils import str_validator


class TextStyles(IntEnum):
    short = 1
    paragraph = 2


@attr.s()
class InputText(InteractiveComponent):
    type: Union[ComponentTypes, int] = attr.ib(
        default=ComponentTypes.INPUT_TEXT, init=False, on_setattr=attr.setters.frozen
    )

    label: str = attr.ib(validator=str_validator)
    style: Union[TextStyles, int] = attr.ib()

    custom_id: Optional[str] = attr.ib(factory=lambda: str(uuid.uuid4()), validator=str_validator)

    placeholder: Optional[str] = attr.ib(default=MISSING, validator=str_validator, kw_only=True)
    value: Optional[str] = attr.ib(default=MISSING, validator=str_validator, kw_only=True)

    required: bool = attr.ib(default=True, kw_only=True)
    min_length: Optional[int] = attr.ib(default=MISSING, kw_only=True)
    max_length: Optional[int] = attr.ib(default=MISSING, kw_only=True)


@attr.s()
class ShortText(InputText):
    style: Union[TextStyles, int] = attr.ib(default=TextStyles.short, kw_only=True)


@attr.s()
class ParagraphText(InputText):
    style: Union[TextStyles, int] = attr.ib(default=TextStyles.paragraph, kw_only=True)


@attr.s()
class Modal(DictSerializationMixin):
    type: Union[CallbackTypes, int] = attr.ib(default=CallbackTypes.MODAL, init=False, on_setattr=attr.setters.frozen)
    title: str = attr.ib(validator=str_validator)
    components: List[InputText] = attr.ib()
    custom_id: Optional[str] = attr.ib(factory=lambda: str(uuid.uuid4()), validator=str_validator)

    def __attrs_post_init__(self):
        if self.custom_id is MISSING:
            self.custom_id = str(uuid.uuid4())

    def to_dict(self):
        data = super().to_dict()
        components = [{"type": ComponentTypes.ACTION_ROW, "components": [c]} for c in data.get("components", [])]
        return {
            "type": data["type"],
            "data": {"custom_id": data["custom_id"], "title": data["title"], "components": components},
        }
