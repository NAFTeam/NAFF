import logging
import re
from base64 import b64encode
from typing import Any, Dict, Union

import aiohttp  # type: ignore

from dis_snek.const import logger_name

log = logging.getLogger(logger_name)

try:
    import orjson as json
except ImportError:
    log.warning("orjson not installed, built-in json library will be used")
    import json


_quotes = {
    '"': '"',
    "‘": "’",
    "‚": "‛",
    "“": "”",
    "„": "‟",
    "⹂": "⹂",
    "「": "」",
    "『": "』",
    "〝": "〞",
    "﹁": "﹂",
    "﹃": "﹄",
    "＂": "＂",
    "｢": "｣",
    "«": "»",
    "‹": "›",
    "《": "》",
    "〈": "〉",
}
_pending_regex = r"(1.*2|[^\s]+)"
_pending_regex = _pending_regex.replace("1", f"[{''.join([k for k in _quotes.keys()])}]")
_pending_regex = _pending_regex.replace("2", f"[{''.join([k for k in _quotes.values()])}]")

arg_parse = re.compile(_pending_regex)
white_space = re.compile(r"\s+")
initial_word = re.compile(r"^([^\s]+)\s*?")


class OverriddenJson:
    @staticmethod
    def dumps(*args, **kwargs) -> str:
        data = json.dumps(*args, **kwargs)
        if isinstance(data, bytes):
            data = data.decode("utf-8")
        return data

    @staticmethod
    def loads(*args, **kwargs) -> dict:
        return json.loads(*args, **kwargs)


async def response_decode(response: aiohttp.ClientResponse) -> Union[Dict[str, Any], str]:
    """
    Return the response text in its correct format, be it dict, or string.

    Args:
        response: the aiohttp response
    Returns:
        the response text field in its correct type
    """
    text = await response.text(encoding="utf-8")

    if response.headers.get("content-type") == "application/json":
        return OverriddenJson.loads(text)
    return text


def get_args(text: str):
    """
    Get arguments from an input text.

    Args:
        text: The text to process
    Returns:
        A list of words
    """
    return arg_parse.findall(text)


def get_first_word(text: str):
    """
    Get a the first word in a string, regardless of whitespace type.

    Args:
        text: The text to process
    Returns:
         The requested word
    """
    found = initial_word.findall(text)
    if len(found) == 0:
        return None
    return found[0]


def _get_mime_type_for_image(data: bytes):
    # taken from d.py, alternative is to use libmagic, which would require users to install libs
    if data.startswith(b"\x89\x50\x4E\x47\x0D\x0A\x1A\x0A"):
        return "image/png"
    elif data[0:3] == b"\xff\xd8\xff" or data[6:10] in (b"JFIF", b"Exif"):
        return "image/jpeg"
    elif data.startswith((b"\x47\x49\x46\x38\x37\x61", b"\x47\x49\x46\x38\x39\x61")):
        return "image/gif"
    elif data.startswith(b"RIFF") and data[8:12] == b"WEBP":
        return "image/webp"
    else:
        raise ValueError("Unsupported image type given")


def _bytes_to_base64_data(data: bytes) -> str:
    mime = _get_mime_type_for_image(data)
    return f"data:{mime};base64,{b64encode(data).decode('ascii')}"
