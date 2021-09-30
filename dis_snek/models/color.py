import colorsys
import re
from enum import Enum
from typing import Tuple

import attr


@attr.s(init=False, slots=True)
class Color:
    hex_regex = re.compile(r"^#(?:[0-9a-fA-F]{3}){1,2}$")

    value: int = attr.ib()

    def __init__(self, color=None):
        color = color or (0, 0, 0)
        if isinstance(color, int):
            self.value = color
        elif isinstance(color, (tuple, list)):
            self.rgb = color
        elif isinstance(color, str):
            if re.match(self.hex_regex, color):
                self.hex = color
            else:
                self.value = BrandColors[color].value  # todo exception handling for better message
        else:
            raise TypeError

    def __str__(self) -> str:
        return self.hex

    # Helper methods

    @staticmethod
    def clamp(x, min_value=0, max_value=255) -> int:
        return max(min_value, min(x, max_value))

    # Constructor methods

    @classmethod
    def from_rgb(cls, r, g, b) -> "Color":
        return cls((r, g, b))

    @classmethod
    def from_hex(cls, value) -> "Color":
        instance = cls()
        instance.hex = value
        return instance

    @classmethod
    def from_hsv(cls, h, s, v) -> "Color":
        instance = cls()
        instance.hsv = h, s, v
        return instance

    # Properties and setter methods

    def _get_byte(self, n) -> int:
        return (self.value >> (8 * n)) & 255

    @property
    def r(self) -> int:
        return self._get_byte(0)

    @property
    def g(self) -> int:
        return self._get_byte(1)

    @property
    def b(self) -> int:
        return self._get_byte(2)

    @property
    def rgb(self) -> Tuple[int, int, int]:
        return self._get_byte(0), self._get_byte(1), self._get_byte(2)

    @property
    def rgb_float(self) -> Tuple[float, float, float]:
        # noinspection PyTypeChecker
        return tuple(v / 255 for v in self.rgb)

    @rgb.setter
    def rgb(self, value: Tuple[int, int, int]):
        # noinspection PyTypeChecker
        r, g, b = (self.clamp(v) for v in value)
        self.value = (r << 16) + (g << 8) + b

    @property
    def hex(self) -> str:
        r, g, b = self.rgb
        return f"#{r:02x}{g:02x}{b:02x}"

    @hex.setter
    def hex(self, value: str):
        value = value.lstrip("#")
        # split hex into 3 parts of 2 digits and convert each to int from base-16 number
        self.rgb = tuple(int(value[i : i + 2], 16) for i in (0, 2, 4))

    @property
    def hsv(self) -> Tuple[float, float, float]:
        return colorsys.rgb_to_hsv(*self.rgb_float)

    @hsv.setter
    def hsv(self, value):
        self.rgb = tuple(round(v * 255) for v in colorsys.hsv_to_rgb(*value))


class BrandColors(Color, Enum):
    """
    A collection of colors complying to the Discord Brand specification

    https://discord.com/branding
    """

    BLURPLE = "#5865F2"
    GREEN = "#57F287"
    YELLOW = "#FEE75C"
    FUCHSIA = "#EB459E"
    RED = "#ED4245"
    WHITE = "#FFFFFF"
    BLACK = "#000000"


class MaterialColors(Color, Enum):
    """
    A collection of material ui colors.

    https://www.materialpalette.com/
    """

    RED = "#F44336"
    PINK = "#E91E63"
    LAVENDER = "#EDB9F5"
    PURPLE = "#9C27B0"
    DEEP_PURPLE = "#673AB7"
    INDIGO = "#3F51B5"
    BLUE = "#2196F3"
    LIGHT_BLUE = "#03A9F4"
    CYAN = "#00BCD4"
    TEAL = "#009688"
    GREEN = "#4CAF50"
    LIGHT_GREEN = "#8BC34A"
    LIME = "#CDDC39"
    YELLOW = "#FFEB3B"
    AMBER = "#FFC107"
    ORANGE = "#FF9800"
    DEEP_ORANGE = "#FF5722"
    BROWN = "#795548"
    GREY = "#9E9E9E"
    BLUE_GREY = "#607D8B"


class FlatUIColors(Color, Enum):
    """
    A collection of flat ui colours.

    https://materialui.co/flatuicolors
    """

    TURQUOISE = "#1ABC9C"
    EMERLAND = "#2ECC71"
    PETERRIVER = "#3498DB"
    AMETHYST = "#9B59B6"
    WETASPHALT = "#34495E"
    GREENSEA = "#16A085"
    NEPHRITIS = "#27AE60"
    BELIZEHOLE = "#2980B9"
    WISTERIA = "#8E44AD"
    MIDNIGHTBLUE = "#2C3E50"
    SUNFLOWER = "#F1C40F"
    CARROT = "#E67E22"
    ALIZARIN = "#E74C3C"
    CLOUDS = "#ECF0F1"
    CONCRETE = "#95A5A6"
    ORANGE = "#F39C12"
    PUMPKIN = "#D35400"
    POMEGRANATE = "#C0392B"
    SILVER = "#BDC3C7"
    ASBESTOS = "#7F8C8D"


# aliases
Colour = Color
BrandColours = BrandColors
MaterialColours = MaterialColors
FlatUIColours = FlatUIColors
