from typing import Dict, Any

import aiohttp

from dis_snek.const import MISSING


class SnakeException(Exception):
    """Base Exception of discord-snakes"""


class BotException(SnakeException):
    """An issue occurred in the client, likely user error"""


class GatewayNotFound(SnakeException):
    """An exception that is raised when the gateway for Discord could not be found"""

    def __init__(self):
        super().__init__("Unable to find discord gateway!")


class LoginError(BotException):
    """The bot failed to login, check your token"""


class HTTPException(SnakeException):
    """A HTTP request resulted in an exception

    Attributes:
        response aiohttp.ClientResponse: The response of the HTTP request
        text str: The text of the exception, could be None
        status int: The HTTP status code
        code int: The discord error code, if one is provided
        route Route: The HTTP route that was used
    """

    def __init__(self, response: aiohttp.ClientResponse, text=MISSING, discord_code=MISSING, **kwargs):
        self.response: aiohttp.ClientResponse = response
        self.status: int = response.status
        self.code: int = discord_code
        self.text: str = text
        self.errors: Any = MISSING
        self.route = kwargs.get("route", MISSING)

        if data := kwargs.get("response_data"):
            if isinstance(data, dict):
                self.text = data.get("message", MISSING)
                self.code = data.get("code", MISSING)
                self.errors = data.get("errors", MISSING)
            else:
                self.text = data

        super().__init__(f"{self.status}|{self.response.reason}: {f'({self.code}) ' if self.code else ''}{self.text}")


class DiscordError(HTTPException):
    """A discord-side error"""


class BadRequest(HTTPException):
    """A bad request was made"""


class Forbidden(HTTPException):
    """You do not have access to this"""


class NotFound(HTTPException):
    """This resource could not be found"""


class RateLimited(HTTPException):
    """Discord is rate limiting this application"""


class WebSocketClosed(SnakeException):
    """The websocket was closed"""

    code: int = 0
    codes: Dict[int, str] = {
        4000: "Unknown Error",
        4001: "Unknown OpCode",
        4002: "Decode Error",
        4003: "Not Authenticated",
        4004: "Authentication Failed",
        4005: "Already Authenticated",
        4007: "Invalid seq",
        4008: "Rate limited",
        4009: "Session Timed Out",
        4010: "Invalid Shard",
        4011: "Sharding Required",
        4012: "Invalid API Version",
        4013: "Invalid Intents",
        4014: "Disallowed Intents",
    }

    def __init__(self, code: int):
        self.code = code
        super().__init__(f"The Websocket closed with code: {code} - {self.codes.get(code, 'Unknown Error')}")


class WebSocketRestart(SnakeException):
    """The websocket closed, and is safe to restart"""

    def __int__(self, resume: bool = False):
        self.resume = resume
        super().__init__("Websocket connection closed... reconnecting")


class ExtensionException(SnakeException):
    """An error occurred with an extension"""


class ExtensionNotFound(ExtensionException):
    """The desired extension was not found"""


class ExtensionLoadException(ExtensionException):
    """An error occurred loading an extension"""


class ScaleLoadException(ExtensionLoadException):
    """A scale failed to load"""
