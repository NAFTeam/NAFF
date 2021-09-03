import uuid
from typing import TYPE_CHECKING, Any, Dict, List, Optional, Union

import attr

from dis_snek.const import SELECTS_MAX_OPTIONS, SELECT_MAX_NAME_LENGTH, ACTION_ROW_MAX_ITEMS
from dis_snek.mixins.serialization import DictSerializationMixin
from dis_snek.models.enums import ButtonStyles, ComponentTypes
from dis_snek.utils.attr_utils import str_validator
from dis_snek.utils.serializer import export_converter, to_dict
from dis_snek.models.discord_objects.emoji import process_emoji

if TYPE_CHECKING:
    from dis_snek.models.discord_objects.emoji import Emoji


class BaseComponent(DictSerializationMixin):
    """
    A base component class. This should never be instantiated.
    """

    def __init__(self) -> None:
        raise NotImplementedError

    @classmethod
    def from_dict_factory(cls, data) -> "TYPE_ALL_COMPONENT":
        data.pop("hash", None)  # TODO Zero clue why discord sometimes include a hash attribute...

        component_type = data.pop("type", None)
        component_class = TYPE_COMPONENT_MAPPING.get(component_type)
        if not component_class:
            raise TypeError(f"Unsupported component type for {data} ({component_type}), please consult the docs.")

        return component_class.from_dict(data)


class InteractiveComponent(BaseComponent):
    """
    A base interactive component class. This should never be instantiated.
    """

    def __eq__(self, other: Any) -> bool:
        if isinstance(other, dict):
            other = BaseComponent.from_dict_factory(other)
            return self.custom_id == other.custom_id and self.type == other.type
        return False


@attr.s(slots=True, eq=False)
class Button(InteractiveComponent):
    """
    :param style: Buttons come in a variety of styles to convey different types of actions.
    :param label: The text that appears on the button, max 80 characters.
    :param emoji: The emoji that appears on the button.
    :param custom_id: A developer-defined identifier for the button, max 100 characters.
    :param url: A url for link-style buttons.
    :param disabled: Disable the button and make it not interactable, default false.
    """

    style: Union[ButtonStyles, int] = attr.ib()
    label: Optional[str] = attr.ib(default=None)
    emoji: Optional[Union["Emoji", dict, str]] = attr.ib(default=None, metadata=export_converter(process_emoji))
    custom_id: Optional[str] = attr.ib(factory=uuid.uuid4, validator=str_validator)
    url: Optional[str] = attr.ib(default=None)
    disabled: bool = attr.ib(default=False)
    type: Union[ComponentTypes, int] = attr.ib(
        default=ComponentTypes.BUTTON, init=False, on_setattr=attr.setters.frozen
    )

    @style.validator
    def _style_validator(self, attribute: str, value: int):
        if not isinstance(value, ButtonStyles) and not value in ButtonStyles.__members__.values():
            raise ValueError(f'Button style type of "{value}" not recognized, please consult the docs.')

    def check_object(self):
        if self.style == ButtonStyles.URL:
            if self.custom_id:
                raise TypeError("A link button cannot have a `custom_id`!")
            if not self.url:
                raise TypeError("A link button must have a `url`!")
        else:
            if self.url:
                raise TypeError("You can't have a URL on a non-link button!")
            if not self.custom_id:
                raise TypeError("You need to have a custom id to identify the button.")

        if not self.label and not self.emoji:
            raise TypeError("You must have at least a label or emoji on a button.")


@attr.s(slots=True)
class SelectOption(BaseComponent):

    label: str = attr.ib(validator=str_validator)
    value: str = attr.ib(validator=str_validator)
    description: Optional[str] = attr.ib(default=None)
    emoji: Optional[Union["Emoji", dict, str]] = attr.ib(default=None, metadata=export_converter(process_emoji))
    default: bool = attr.ib(default=False)

    @label.validator
    def _label_validator(self, attribute: str, value: str):
        if not value or len(value) > SELECT_MAX_NAME_LENGTH:
            raise ValueError("Label length should be between 1 and 100.")

    @value.validator
    def _value_validator(self, attribute: str, value: str):
        if not value or len(value) > SELECT_MAX_NAME_LENGTH:
            raise ValueError("Value length should be between 1 and 100.")

    @description.validator
    def _description_validator(self, attribute: str, value: str):
        if value is not None and len(value) > SELECT_MAX_NAME_LENGTH:
            raise ValueError("Description length must be 100 or lower.")


@attr.s(slots=True, eq=False)
class Select(InteractiveComponent):
    """
    :param options: The choices in the select, max 25.
    :param custom_id: A developer-defined identifier for the button, max 100 characters.
    :param placeholder: The custom placeholder text to show if nothing is selected, max 100 characters.
    :param min_values: The minimum number of items that must be chosen. (default 1, min 0, max 25)
    :param max_values: The maximum number of items that can be chosen. (default 1, max 25)
    :param disabled: Disable the select and make it not interactable, default false.
    :param type: The action role type number defined by discord. This cannot be modified.
    """

    options: List[dict] = attr.ib(factory=list)
    custom_id: str = attr.ib(factory=uuid.uuid4, validator=str_validator)
    placeholder: str = attr.ib(default=None)
    min_values: Optional[int] = attr.ib(default=1)
    max_values: Optional[int] = attr.ib(default=1)
    disabled: bool = attr.ib(default=False)
    type: Union[ComponentTypes, int] = attr.ib(
        default=ComponentTypes.SELECT, init=False, on_setattr=attr.setters.frozen
    )

    def __len__(self) -> int:
        return len(self.options)

    @placeholder.validator
    def _placeholder_validator(self, attribute: str, value: str):
        if value is not None and len(value) > SELECT_MAX_NAME_LENGTH:
            raise ValueError("Placeholder length must be 100 or lower.")

    @min_values.validator
    def _min_values_validator(self, attribute: str, value: int):
        if value < 0:
            raise ValueError("Select min value cannot be a negative number.")

    @max_values.validator
    def _max_values_validator(self, attribute: str, value: int):
        if value < 0:
            raise ValueError("Select max value cannot be a negative number.")

    def check_object(self):
        if not self.custom_id:
            raise TypeError("You need to have a custom id to identify the select.")

        if not self.options:
            raise TypeError("Selects needs to have at least 1 option.")

        if len(self.options) > SELECTS_MAX_OPTIONS:
            raise TypeError("Selects can only hold 25 options")

        if self.max_values < self.min_values:
            raise TypeError("Selects max value cannot be less than min value.")

    def add_option(self, option: Union[SelectOption, dict]):
        self.options.append(option)


@attr.s(slots=True, init=False)
class ActionRow(BaseComponent):
    """
    :param components:
    :param type: The action role type number defined by discord. This cannot be modified.
    """

    _max_items = ACTION_ROW_MAX_ITEMS

    components: List[Union[dict, Select, Button]] = attr.ib(factory=list)
    type: Union[ComponentTypes, int] = attr.ib(
        default=ComponentTypes.ACTION_ROW, init=False, on_setattr=attr.setters.frozen
    )

    def __init__(self, *components: Union[dict, Select, Button]) -> None:
        self.__attrs_init__(components)
        self.components = [self._component_checks(c) for c in self.components]

    def __len__(self) -> int:
        return len(self.components)

    @classmethod
    def from_dict(cls, data):
        return cls(*data["components"])

    def _component_checks(self, component: Union[dict, Select, Button]):
        if isinstance(component, dict):
            component = BaseComponent.from_dict_factory(component)

        if not issubclass(type(component), InteractiveComponent):
            raise TypeError("You can only add select or button to the action row.")

        component.check_object()
        return component

    def check_object(self):
        if not (0 < len(self.components) <= ActionRow._max_items):
            raise TypeError(f"Number of components in one row should be between 1 and {ActionRow._max_items}.")

        if any(x.type == ComponentTypes.SELECT for x in self.components) and len(self.components) != 1:
            raise TypeError("Action row must have only one select component and nothing else.")

    def add_components(self, *components: Union[dict, Button, Select]):
        """
        Add one or more component(s) to this action row

        :param components:
        """
        for c in components:
            self.components.append(self._component_checks(c))


def process_components(
    components: Optional[
        Union[List[List[Union[BaseComponent, Dict]]], List[Union[BaseComponent, Dict]], BaseComponent, Dict]
    ]
) -> List[Dict]:
    """
    Process the passed components into a format discord will understand.

    :param components: List of dict / components to process
    """
    if not components:
        # Its just empty, so nothing to process.
        return

    if isinstance(components, dict):
        # If a naked dictionary is passed, assume the user knows what they're doing and send it blindly
        # after wrapping it in a list for discord
        return [components]

    if issubclass(type(components), BaseComponent):
        # Naked component was passed
        components = [components]

    if isinstance(components, list):
        if all(isinstance(c, dict) for c in components):
            # user has passed a list of dicts, this is the correct format, blindly send it
            return components

        if all(isinstance(c, list) for c in components):
            # list of lists... actionRow-less sending
            return [ActionRow(*row).to_dict() for row in components]

        if all(issubclass(type(c), InteractiveComponent) for c in components):
            # list of naked components
            return [ActionRow(*components).to_dict()]

        if all(isinstance(c, ActionRow) for c in components):
            # we have a list of action rows
            return [action_row.to_dict() for action_row in components]

    raise ValueError(f"Invalid components: {components}")


TYPE_ALL_COMPONENT = Union[ActionRow, Button, Select]


TYPE_COMPONENT_MAPPING = {
    ComponentTypes.ACTION_ROW: ActionRow,
    ComponentTypes.BUTTON: Button,
    ComponentTypes.SELECT: Select,
}
