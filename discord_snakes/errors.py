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

    code = 0
    codes = {
        4000: "4000 - Unknown Error",
        4001: "4001 - Unknown OpCode",
        4002: "4002 - Decode Error",
        4003: "4003 - Not Authenticated",
        4004: "4004 - Authentication Failed",
        4005: "4005 - Already Authenticated",
        4007: "4007 - Invalid seq",
        4008: "4008 - Rate limited",
        4009: "4009 - Session Timed Out",
        4010: "4010 - Invalid Shard",
        4011: "4011 - Sharding Required",
        4012: "4012 - Invalid API Version",
        4013: "4013 - Invalid Intents",
        4014: "4014 - Disallowed Intents",
    }

    def __init__(self, code):
        self.code = code
        super().__init__(f"The Websocket closed with code: {self.codes.get(code, f'{code} - Unknown Error')}")


class WebSocketRestart(Exception):
    """The websocket closed, and is safe to restart"""

    resume = False

    def __int__(self, resume=False):
        self.resume = resume
        super().__init__("Websocket connection closed... reconnecting")
