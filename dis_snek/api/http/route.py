from typing import TYPE_CHECKING, Any, ClassVar, Optional
from urllib.parse import quote as _uriquote


if TYPE_CHECKING:
    from dis_snek.models.discord.snowflake import Snowflake_Type


class Route:
    BASE: ClassVar[str] = "https://discord.com/api/v9"
    path: str
    params: dict[str, str | int]

    webhook_id: Optional["Snowflake_Type"]
    webhook_token: Optional[str]

    def __init__(self, method: str, path: str, **parameters: Any):
        self.path: str = path
        self.method: str = method
        self.params = parameters

        self.webhook_id = parameters.get("webhook_id")
        self.webhook_token = parameters.get("webhook_token")

    def __hash__(self):
        return hash(self.rl_bucket)

    def __repr__(self):
        return f"<Route {self.endpoint}>"

    def __str__(self):
        return self.endpoint

    @property
    def bucket(self) -> str:
        """This routes bucket"""
        return f"{self.params.get('channel_id')}:{self.params.get('guild_id')}:{self.path}"

    @property
    def rl_bucket(self) -> str:
        """Sane bucket for use in rate limiting including method"""
        return f"{self.method}::{self.bucket}"

    @property
    def endpoint(self) -> str:
        """The endpoint for this route"""
        return f"{self.method} {self.path}"

    @property
    def url(self) -> str:
        """The full url for this route"""
        return f"{self.BASE}{self.path}".format_map(
            {k: _uriquote(v) if isinstance(v, str) else v for k, v in self.params.items()}
        )
