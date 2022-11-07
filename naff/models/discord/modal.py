import uuid
from enum import IntEnum
from typing import Union, Optional, List

import attrs

from naff.client.const import MISSING
from naff.client.mixins.nattrs import Nattrs, Field
from naff.client.utils.attr_utils import str_validator
from naff.models.discord.components import InteractiveComponent, ComponentTypes
from naff.models.naff.application_commands import CallbackTypes

__all__ = ("InputText", "Modal", "ParagraphText", "ShortText", "TextStyles")


class TextStyles(IntEnum):
    SHORT = 1
    PARAGRAPH = 2


class InputText(InteractiveComponent):
    """An input component for modals"""

    type: Union[ComponentTypes, int] = Field(
        repr=False, default=ComponentTypes.INPUT_TEXT, init=False, on_setattr=attrs.setters.frozen
    )

    label: str = Field(repr=False, validator=str_validator)
    """the label for this component"""
    style: Union[TextStyles, int] = Field(
        repr=False,
    )
    """the Text Input Style for single or multiple lines input"""

    custom_id: Optional[str] = Field(repr=False, factory=lambda: str(uuid.uuid4()), validator=str_validator)
    """a developer-defined identifier for the input, max 100 characters"""

    placeholder: Optional[str] = Field(repr=False, default=MISSING, validator=str_validator, kw_only=True)
    """custom placeholder text if the input is empty, max 100 characters"""
    value: Optional[str] = Field(repr=False, default=MISSING, validator=str_validator, kw_only=True)
    """a pre-filled value for this component, max 4000 characters"""

    required: bool = Field(repr=False, default=True, kw_only=True)
    """whether this component is required to be filled, default true"""
    min_length: Optional[int] = Field(repr=False, default=MISSING, kw_only=True)
    """the minimum input length for a text input, min 0, max 4000"""
    max_length: Optional[int] = Field(repr=False, default=MISSING, kw_only=True)
    """the maximum input length for a text input, min 1, max 4000. Must be more than min_length."""


class ShortText(InputText):
    """A single line input component for modals"""

    style: Union[TextStyles, int] = Field(repr=False, default=TextStyles.SHORT, kw_only=True)


class ParagraphText(InputText):
    """A multi line input component for modals"""

    style: Union[TextStyles, int] = Field(repr=False, default=TextStyles.PARAGRAPH, kw_only=True)


class Modal(Nattrs):
    """Form submission style component on discord"""

    type: Union[CallbackTypes, int] = Field(
        repr=False, default=CallbackTypes.MODAL, init=False, on_setattr=attrs.setters.frozen
    )
    title: str = Field(repr=False, validator=str_validator)
    """the title of the popup modal, max 45 characters"""
    components: List[InputText] = Field(
        repr=False,
    )
    """between 1 and 5 (inclusive) components that make up the modal"""
    custom_id: Optional[str] = Field(repr=False, factory=lambda: str(uuid.uuid4()), validator=str_validator)
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
