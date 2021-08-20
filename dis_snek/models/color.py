import colorsys
import enum
import re
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
        if isinstance(color, (tuple, list)):
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
    def clamp(x, min_value=0, max_value=255):
        return max(min_value, min(x, max_value))

    # Constructor methods

    @classmethod
    def from_rgb(cls, r, g, b):
        return cls((r, g, b))

    @classmethod
    def from_hex(cls, value):
        instance = cls()
        instance.hex = value
        return instance

    @classmethod
    def from_hsv(cls, h, s, v):
        instance = cls()
        instance.hsv = h, s, v
        return instance

    # Properties and setter methods

    def _get_byte(self, n):
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


# maybe should be just a dict but not sure
# or just str enum but no so sure again
class BrandColors(Color, enum.Enum):
    # https://discord.com/branding
    blurple = "#5865F2"
    green = "#57F287"
    yellow = "#FEE75C"
    fuchsia = "#EB459E"
    red = "#ED4245"
    white = "#FFFFFF"
    black = "#000000"
