"""
The MIT License (MIT).

Copyright (c) 2021 - present LordOfPolls

Permission is hereby granted, free of charge, to any person obtaining a
copy of this software and associated documentation files (the "Software"),
to deal in the Software without restriction, including without limitation
the rights to use, copy, modify, merge, publish, distribute, sublicense,
and/or sell copies of the Software, and to permit persons to whom the
Software is furnished to do so, subject to the following conditions:
The above copyright notice and this permission notice shall be included in
all copies or substantial portions of the Software.
THE SOFTWARE IS PROVIDED "AS IS", WITHOUT WARRANTY OF ANY KIND, EXPRESS
OR IMPLIED, INCLUDING BUT NOT LIMITED TO THE WARRANTIES OF MERCHANTABILITY,
FITNESS FOR A PARTICULAR PURPOSE AND NONINFRINGEMENT. IN NO EVENT SHALL THE
AUTHORS OR COPYRIGHT HOLDERS BE LIABLE FOR ANY CLAIM, DAMAGES OR OTHER
LIABILITY, WHETHER IN AN ACTION OF CONTRACT, TORT OR OTHERWISE, ARISING
FROM, OUT OF OR IN CONNECTION WITH THE SOFTWARE OR THE USE OR OTHER
DEALINGS IN THE SOFTWARE.
"""
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

    :param response: the aiohttp response
    :return: the response text field in its correct type
    """
    text = await response.text(encoding="utf-8")

    if response.headers.get("content-type") == "application/json":
        return OverriddenJson.loads(text)
    return text


def get_args(text: str):
    """
    Get arguments from an input text.

    :param text: The text to process
    :return: A list of words
    """
    return arg_parse.findall(text)


def get_first_word(text: str):
    """
    Get a the first word in a string, regardless of whitespace type.
    :param text: The text to process
    :return: The requested word
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
