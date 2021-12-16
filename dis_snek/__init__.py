"""
Dis-Snek
~~~~~~~~~~~~~~~~~~~
A Python API wrapper for Discord
:copyright: (c) 2021-present LordOfPolls
:license: MIT, see LICENSE for more details.
"""

from .const import __version__

from .client import Snake
from .annotations import *
from .models import *
from .errors import *

from . import utils, const
