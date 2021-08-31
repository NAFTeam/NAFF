import sys

_ver_info = sys.version_info

__version__ = "0.0.0"
__repo_url__ = "https://github.com/LordOfPolls/dis_snek"
__py_version__ = f"{_ver_info[0]}.{_ver_info[1]}"
logger_name = "dis.snek"

GLOBAL_SCOPE = 0
ACTION_ROW_MAX_ITEMS = 5
SELECTS_MAX_OPTIONS = 25
SELECT_MAX_NAME_LENGTH = 100

CONTEXT_MENU_NAME_LENGTH = 32
SLASH_CMD_NAME_LENGTH = 32
SLASH_CMD_MAX_DESC_LENGTH = 100
SLASH_CMD_MAX_OPTIONS = 25
SLASH_OPTION_NAME_LENGTH = 100
