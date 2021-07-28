from typing import Dict, Union, Any

import aiohttp
import orjson


async def response_decode(response: aiohttp.ClientResponse) -> Union[Dict[str, Any], str]:
    """
    Returns the response text in its correct format, be it dict, or string
    :param response: the aiohttp response
    :return: the response text field in its correct type
    """
    text = await response.text(encoding="utf-8")

    if response.headers.get("content-type") == "application/json":
        return orjson.loads(text)
    return text
