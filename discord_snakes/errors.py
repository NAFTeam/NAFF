from typing import Optional


class SnakeException(Exception):
    """Base Exception of discord-snakes"""

    def __init__(self, message):
        self.message = message
        super().__init__(self.message)


class WebsocketClosed(SnakeException):
    """The websocket is closed"""


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
