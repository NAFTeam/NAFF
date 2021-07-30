import logging
import uuid
from typing import List, Optional, Union

from dis_snek.const import logger_name
from dis_snek.models.enums import ComponentType, ButtonStyle

log = logging.getLogger(logger_name)


class BaseComponent:
    """
    A base component class
    """

    __slots__ = "_type", "custom_id"

    def __eq__(self, other):
        if isinstance(other, dict):
            other = convert_dict(other)

        if self.custom_id == other.custom_id and self.type == other.type:
            return True
        return False

    @property
    def type(self):
        return self._type

    @property
    def to_dict(self):
        return self.__dict__

    def _checks(self):
        """Checks all attributes of this object are valid"""
        if self.custom_id is not None and not isinstance(self.custom_id, str):
            self.custom_id = str(self.custom_id)
            log.warning(
                "Custom_id has been automatically converted to a string. Please use strings in future\n"
                "Note: Discord will always return custom_id as a string"
            )


class Button(BaseComponent):
    __slots__ = "style", "label", "emoji", "url", "disabled"

    def __init__(
        self,
        style: Union[ButtonStyle, int],
        label: str = None,
        emoji: Union[dict] = None,
        custom_id: str = None,
        url: str = None,
        disabled: bool = False,
    ):
        self._type: Union[ComponentType, int] = ComponentType.BUTTON
        self.style: Union[ButtonStyle, int] = style
        self.label: Optional[str] = label
        self.emoji: Optional[dict] = emoji
        self.custom_id: str = custom_id
        self.url: Optional[str] = url
        self.disabled: bool = disabled

    def _checks(self):
        super()._checks()

        if self.style == ButtonStyle.URL:
            if self.custom_id:
                raise TypeError("A link button cannot have a `custom_id`!")
            if not self.url:
                raise TypeError("A link button must have a `url`!")
        elif self.url:
            raise TypeError("You can't have a URL on a non-link button!")

        if not self.label and not self.emoji:
            raise TypeError("You must have at least a label or emoji on a button.")

    @property
    def to_dict(self) -> dict:
        """
        Returns a dictionary representing this component, that discord can process
        """
        self._checks()
        to_return = {"type": self._type, "style": self.style, "disabled": self.disabled}
        if self.label:
            to_return["label"] = self.label
        if self.emoji:
            to_return["emoji"] = self.emoji
        if self.style == ButtonStyle.URL:
            to_return["url"] = self.url
        else:
            to_return["custom_id"] = self.custom_id or str(uuid.uuid4())

        return to_return


class SelectOption(BaseComponent):
    __slots__ = "label", "value", "emoji", "description", "default"

    def __init__(self, label: str, value: str, emoji: None, description: str = None, default: bool = False):
        self.label: str = label
        self.value: str = value
        self.emoji: Optional[dict] = emoji
        self.description: Optional[str] = description
        self.default: bool = default
        self.checks()

    def checks(self):
        if not len(self.label) or len(self.label) > 25:
            raise ValueError("Label length should be between 1 and 25.")

        if not isinstance(self.value, str):
            self.value = str(self.value)
            log.warning(
                "Value has been automatically converted to a string. Please use strings in future\n"
                "Note: Discord will always return value as a string"
            )

        if not len(self.value) or len(self.value) > 100:
            raise ValueError("Value length should be between 1 and 100.")

        if self.description is not None and len(self.description) > 50:
            raise ValueError("Description length must be 50 or lower.")

    @property
    def custom_id(self):
        return self.value

    @custom_id.setter
    def custom_id(self, value):
        self.value = value

    @property
    def to_dict(self) -> dict:
        """
        Returns a dictionary representing this component, that discord can process
        """
        self.checks()
        return {
            "label": self.label,
            "value": self.value,
            "description": self.description,
            "default": self.default,
            "emoji": self.emoji,
        }


class Select(BaseComponent):
    __slots__ = (
        "options",
        "placeholder",
        "max_values",
        "min_values",
        "disabled",
    )

    def __init__(
        self,
        options: List[dict],
        custom_id: str = None,
        placeholder: str = None,
        min_values: int = None,
        max_values: int = None,
        disabled: bool = False,
    ):
        self._type: Union[ComponentType, int] = ComponentType.SELECT
        self.custom_id: str = custom_id
        self.options: List[dict, SelectOption] = options
        self.placeholder: Optional = placeholder
        self.max_values: Optional[int] = min_values
        self.min_values: Optional[int] = max_values
        self.disabled: bool = disabled

    def __len__(self) -> int:
        return len(self.options)

    def _checks(self):
        super()._checks()

        if len(self.options) > 25:
            raise TypeError("Options length should be between 1 and 25.")

    @property
    def to_dict(self) -> dict:
        """
        Returns a dictionary representing this component, that discord can process
        """
        self._checks()

        if not self.options or len(self.options) > 25:
            raise TypeError("Selects can only hold 25 options")
        options = []
        for opt in self.options:
            if isinstance(opt, SelectOption):
                opt = opt.to_dict
            options.append(opt)
        return {
            "type": self._type,
            "options": options,
            "custom_id": self.custom_id or str(uuid.uuid4()),
            "placeholder": self.placeholder or "",
            "min_values": self.min_values,
            "max_values": self.max_values,
            "disabled": self.disabled,
        }

    def add_checks(self, option):
        if not isinstance(option, SelectOption) and not isinstance(dict):
            raise TypeError("Only SelectOption objects, or dicts representing them are supported")

        if self.options == 25:
            raise TypeError("Selects can only hold 25 options")

    def add_option(self, option: Union[SelectOption, dict]):
        self.add_checks(option)
        self.options.append(option)


class ActionRow:
    __slots__ = "_type", "_components", "max_items"

    def __init__(self, *components: Union[dict, Select, Button]):
        self._type = ComponentType.ACTION_ROW

        self._components = []

        self.max_items = 5

        for comp in components:
            self.append(comp)

    def __len__(self) -> int:
        return len(self._components)

    def _checks(self):
        if len(self.components) == 0 or len(self.components) > 5:
            raise TypeError("Number of components in one row should be between 1 and 5.")

        if any(x.type == ComponentType.SELECT for x in self._components) and len(self._components) != 1:
            raise TypeError("Action row must have only one select component and nothing else")

    def append_checks(self, component):
        # todo: fix this mess
        # yes Striga, i see you looking here and screaming, is bad code. ill fix it later

        def check_single_component(_comp):
            if isinstance(_comp, dict):
                # convert dict into object
                if _comp["type"] == ComponentType.BUTTON:
                    _comp = Button(
                        style=_comp.get("style"),
                        label=_comp.get("label"),
                        emoji=_comp.get("emoji"),
                        custom_id=_comp.get("custom_id"),
                        url=_comp.get("url"),
                        disabled=_comp.get("disabled", False),
                    )
                elif _comp["type"] == ComponentType.SELECT:
                    _comp = Select(
                        custom_id=_comp.get("custom_id"),
                        options=_comp.get("options"),
                        placeholder=_comp.get("placeholder"),
                        max_values=_comp.get("max_values"),
                        min_values=_comp.get("min_values"),
                        disabled=_comp.get("disabled", False),
                    )

            if any(x.type == ComponentType.SELECT for x in self._components):
                raise TypeError("Action row must have only one select component and nothing else")
            elif _comp.type == ComponentType.SELECT and len(self) != 0:
                raise TypeError("Action row must have only one select component and nothing else")

        if len(self) == self.max_items:
            # ensure action row does not overflow
            if len(self._components) == 5:
                raise TypeError("Number of components in one row should be between 1 and 5.")

        if isinstance(component, list):
            # list of components
            if not all(isinstance(x, (dict, ActionRow, Button, Select)) for x in component):
                raise TypeError("Action rows can only hold component objects or dictionaries representing them")
            if len(component) + len(self) > 5:
                raise TypeError("Number of components in one row should be between 1 and 5.")

            for comp in component:
                check_single_component(comp)

        else:
            check_single_component(component)

        return component

    @property
    def components(self) -> list:
        return self._components

    @property
    def type(self):
        return self._type

    @property
    def to_dict(self) -> dict:
        """
        Returns a dictionary representing this component, that discord can process
        """
        self._checks()

        _components = []
        for comp in self.components:
            _components.append(comp.to_dict)
        return {"type": self._type, "components": _components}

    def append(self, component: Union[dict, Button, Select]):
        """Add a component to this action row"""
        component = self.append_checks(component)
        self._components.append(component)

    def remove(self, index: int):
        del self._components[index]


def convert_dict(component: dict) -> Union[ActionRow, Button, Select]:
    """
    Converts a dict representation of a component into its object form

    :param component: A component dict
    """
    if component.get("type") == ComponentType.ACTIONROW:
        row = ActionRow()
        for comp in component.get("components"):
            row.append(convert_dict(comp))
        return row

    elif component.get("type") == ComponentType.BUTTON:
        return Button(
            label=component.get("label"),
            custom_id=component.get("custom_id"),
            style=component.get("style"),
            disabled=component.get("disabled", False),
            emoji=component.get("emoji"),
        )

    elif component.get("type") == ComponentType.SELECT:
        return Select(
            options=component.get("options"),
            custom_id=component.get("custom_id"),
            placeholder=component.get("placeholder"),
            min_values=component.get("min_values"),
            max_values=component.get("max_values"),
            disabled=component.get("disabled", False),
        )

    else:
        raise TypeError(f"Unknown component type of {component} ({type(component)}). " f"Expected str, dict or list")
