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
import re
from typing import Any, Dict, Union

import aiohttp  # type: ignore

try:
    import orjson as json
except ImportError:
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
