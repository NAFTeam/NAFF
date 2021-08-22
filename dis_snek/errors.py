from typing import Dict


class SnakeException(Exception):
    """Base Exception of discord-snakes"""

    def __init__(self, message):
        self.message = message
        super().__init__(self.message)


class HTTPError(SnakeException):
    """A HTTP Error Occurred"""

    def __init__(self, message, route=None, code=None, resp=None):
        self.status_code = code
        self.route = route
        self.response = resp
        super().__init__(message)


class DiscordError(HTTPError):
    """A discord-side error"""


class BadRequest(HTTPError):
    """A bad request was made"""


class Forbidden(HTTPError):
    """You do not have access to this"""


class NotFound(HTTPError):
    """This resource could not be found"""


class RateLimited(HTTPError):
    """Discord is rate limiting this application"""


class GatewayNotFound(SnakeException):
    """An exception that is raised when the gateway for Discord could not be found"""

    def __init__(self):
        super().__init__("Unable to find gateway...")


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


class WebSocketRestart(Exception):
    """The websocket closed, and is safe to restart"""

    resume: bool = False

    def __int__(self, resume: bool = False):
        self.resume = resume
        super().__init__("Websocket connection closed... reconnecting")
