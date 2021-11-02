"""
Constants used throughout Snek.

attributes:
    __version__ str: The version of the library.
    __repo_url__ str: The URL of the repository.
    __py_version__ str: The python version in use.
    logger_name str: The logger name used by Snek.
    kwarg_spam bool: Should ``unused kwargs`` be logged.

    ACTION_ROW_MAX_ITEMS int: The maximum number of items in an action row.
    SELECTS_MAX_OPTIONS int: The maximum number of options a select may have.
    SELECT_MAX_NAME_LENGTH int: The max length of a select's name.

    CONTEXT_MENU_NAME_LENGTH int: The max length of a context menu's name.
    SLASH_CMD_NAME_LENGTH int: The max length of a slash command's name.
    SLASH_CMD_MAX_DESC_LENGTH int: The maximum length of a slash command's description.
    SLASH_CMD_MAX_OPTIONS int: The maximum number of options a slash command may have.
    SLASH_OPTION_NAME_LENGTH int: The maximum length of a slash option's name.

    EMBED_MAX_NAME_LENGTH int: The maximum length for an embed title
    EMBED_MAX_DESC_LENGTH int: The maximum length for an embed description
    EMBED_MAX_FIELDS int: The maximum number of fields for an embed
    EMBED_TOTAL_MAX int: The total combined number of characters for an embed
    PREMIUM_GUILD_LIMITS dict: Limits granted per premium level of a guild

    GLOBAL_SCOPE _sentinel: A sentinel that represents a global scope for application commands.
    MENTION_PREFIX _sentinel: A sentinel representing the bot will be mentioned for a prefix
    MISSING _sentinel: A sentinel value that indicates something has not been set
"""
import sys
from collections import defaultdict
from importlib.metadata import version as _v

import sentinel

_ver_info = sys.version_info

try:
    __version__ = _v("dis-snek")
except:
    __version__ = "0.0.0"
__repo_url__ = "https://github.com/LordOfPolls/dis_snek"
__py_version__ = f"{_ver_info[0]}.{_ver_info[1]}"
logger_name = "dis.snek"
kwarg_spam = False

DISCORD_EPOCH = 1420070400000

ACTION_ROW_MAX_ITEMS = 5
SELECTS_MAX_OPTIONS = 25
SELECT_MAX_NAME_LENGTH = 100

CONTEXT_MENU_NAME_LENGTH = 32
SLASH_CMD_NAME_LENGTH = 32
SLASH_CMD_MAX_DESC_LENGTH = 100
SLASH_CMD_MAX_OPTIONS = 25
SLASH_OPTION_NAME_LENGTH = 100

EMBED_MAX_NAME_LENGTH = 256
EMBED_MAX_DESC_LENGTH = 4096
EMBED_MAX_FIELDS = 25
EMBED_TOTAL_MAX = 6000

GLOBAL_SCOPE = sentinel.create(
    "GLOBAL_SCOPE",
    (int,),
    cls_dict={
        "__name__": "GLOBAL_SCOPE",
        "__getattr__": lambda x, y: 0,
        "__hash__": lambda _: hash(0),
        "__bool__": lambda _: False,
    },
)

MISSING = sentinel.create(
    "MISSING",
    cls_dict={
        "__eq__": lambda x, y: x.__name__ == y.__name__ if hasattr(y, "__name__") else False,
        "__name__": "MISSING",
        "__getattr__": lambda x, y: None,
        "__bool__": lambda _: False,
    },
)


MENTION_PREFIX = sentinel.create(
    "MENTION_PREFIX",
    cls_dict={
        "__name__": "MENTION_PREFIX",
        "__eq__": lambda x, y: x.__name__ == y.__name__ if hasattr(y, "__name__") else False,
        # i would love for this to have a `__str__` that returns a mention string, but thats not viable
    },
)


PREMIUM_GUILD_LIMITS = defaultdict(
    lambda: {"emoji": 50, "stickers": 0, "bitrate": 96000, "filesize": 8388608},
    {
        1: {"emoji": 100, "stickers": 15, "bitrate": 128000, "filesize": 8388608},
        2: {"emoji": 150, "stickers": 30, "bitrate": 256000, "filesize": 52428800},
        3: {"emoji": 250, "stickers": 60, "bitrate": 384000, "filesize": 104857600},
    },
)
