"""
Constants used throughout Snek.

attributes:
    __version__ str: The version of the library.
    __repo_url__ str: The URL of the repository.
    __py_version__ str: The python version in use.
    logger_name str: The logger name used by Snek.
    kwarg_spam bool: Should ``unused kwargs`` be logged.

    GLOBAL_SCOPE int: Represents a global scope.
    ACTION_ROW_MAX_ITEMS int: The maximum number of items in an action row.
    SELECTS_MAX_OPTIONS int: The maximum number of options a select may have.
    SELECT_MAX_NAME_LENGTH int: The max length of a select's name.

    CONTEXT_MENU_NAME_LENGTH int: The max length of a context menu's name.
    SLASH_CMD_NAME_LENGTH int: The max legnth of a slash command's name.
    SLASH_CMD_MAX_DESC_LENGTH int: The maximum length of a slash command's description.
    SLASH_CMD_MAX_OPTIONS int: The maximum number of options a slash command may have.
    SLASH_OPTION_NAME_LENGTH int: The maximum length of a slash option's name.

    EMBED_MAX_NAME_LENGTH int: The maximum length for an embed title
    EMBED_MAX_DESC_LENGTH int: The maximum length for an embed description
    EMBED_MAX_FIELDS int: The maximum number of fields for an embed
    EMBED_TOTAL_MAX int: The total combined number of characters for an embed

    MISSING _sentinel: A sentinel value that indicates something has not been set
"""

import sys
import sentinel
import dis_snek.models.events as events


_ver_info = sys.version_info


__version__ = "0.0.0"
__repo_url__ = "https://github.com/LordOfPolls/dis_snek"
__py_version__ = f"{_ver_info[0]}.{_ver_info[1]}"
logger_name = "dis.snek"
kwarg_spam = False

GLOBAL_SCOPE = 0
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

MISSING = sentinel.create(
    cls_dict={
        "__eq__": lambda x, y: x.__name__ == y.__name__ if hasattr(y, "__name__") else False,
        "__name__": "MISSING",
    }
)
