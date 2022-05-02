import uuid
from enum import IntEnum
from typing import Union, Optional, List

import attrs

from naff.client.const import MISSING
from naff.client.mixins.serialization import DictSerializationMixin
from naff.models.naff.application_commands import CallbackTypes
from naff.models.discord.components import InteractiveComponent, ComponentTypes
from naff.client.utils.attr_utils import define, field, str_validator

__all__ = ("InputText", "Modal", "ParagraphText", "ShortText", "TextStyles")


class TextStyles(IntEnum):
    SHORT = 1
    PARAGRAPH = 2


@define(kw_only=False)
class InputText(InteractiveComponent):
    """An input component for modals"""

    type: Union[ComponentTypes, int] = field(
        default=ComponentTypes.INPUT_TEXT, init=False, on_setattr=attrs.setters.frozen
    )

    label: str = field(validator=str_validator)
    """the label for this component"""
    style: Union[TextStyles, int] = field()
    """the Text Input Style for single or multiple lines input"""

    custom_id: Optional[str] = field(factory=lambda: str(uuid.uuid4()), validator=str_validator)
    """a developer-defined identifier for the input, max 100 characters"""

    placeholder: Optional[str] = field(default=MISSING, validator=str_validator, kw_only=True)
    """custom placeholder text if the input is empty, max 100 characters"""
    value: Optional[str] = field(default=MISSING, validator=str_validator, kw_only=True)
    """a pre-filled value for this component, max 4000 characters"""

    required: bool = field(default=True, kw_only=True)
    """whether this component is required to be filled, default true"""
    min_length: Optional[int] = field(default=MISSING, kw_only=True)
    """the minimum input length for a text input, min 0, max 4000"""
    max_length: Optional[int] = field(default=MISSING, kw_only=True)
    """the maximum input length for a text input, min 1, max 4000. Must be more than min_length."""


@define(kw_only=False)
class ShortText(InputText):
    """A single line input component for modals"""

    style: Union[TextStyles, int] = field(default=TextStyles.SHORT, kw_only=True)


@define(kw_only=False)
class ParagraphText(InputText):
    """A multi line input component for modals"""

    style: Union[TextStyles, int] = field(default=TextStyles.PARAGRAPH, kw_only=True)


@define(kw_only=False)
class Modal(DictSerializationMixin):
    """Form submission style component on discord"""

    type: Union[CallbackTypes, int] = field(default=CallbackTypes.MODAL, init=False, on_setattr=attrs.setters.frozen)
    title: str = field(validator=str_validator)
    """the title of the popup modal, max 45 characters"""
    components: List[InputText] = field()
    """between 1 and 5 (inclusive) components that make up the modal"""
    custom_id: Optional[str] = field(factory=lambda: str(uuid.uuid4()), validator=str_validator)
    """a developer-defined identifier for the component, max 100 characters"""

    def __attrs_post_init__(self) -> None:
        if self.custom_id is MISSING:
            self.custom_id = str(uuid.uuid4())

    def to_dict(self) -> dict:
        data = super().to_dict()
        components = [{"type": ComponentTypes.ACTION_ROW, "components": [c]} for c in data.get("components", [])]
        return {
            "type": data["type"],
            "data": {"custom_id": data["custom_id"], "title": data["title"], "components": components},
        }
