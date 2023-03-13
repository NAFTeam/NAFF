from warnings import warn

from .client import *
from .client.const import *
from .models import *
from .api import *
from . import ext


warn("The naff package is deprecated and will be removed in a future version. Please migrate to interactions.py where future development will be taking place. https://github.com/interactions-py/interactions.py", DeprecationWarning, stacklevel=2)

########################################################################################################################
# Credits
# LordOfPolls -- Lead Contributor
# AlbertUnruh -- Contributor
# artem30801 -- Contributor
# Astrea49 -- Contributor
# benwoo1110 -- Contributor
# Bluenix2 -- Contributor
# Kigstn -- Contributor
# leestarb -- Contributor
# silasary -- Contributor
# Wolfhound905 -- Contributor
# zevaryx -- Contributor
########################################################################################################################
