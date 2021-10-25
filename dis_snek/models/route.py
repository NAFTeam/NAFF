from typing import TYPE_CHECKING, Any, ClassVar, Optional
from urllib.parse import quote as _uriquote

if TYPE_CHECKING:
    from dis_snek.models.snowflake import Snowflake_Type


class Route:
    BASE: ClassVar[str] = "https://discord.com/api/v9"

    def __init__(self, method: str, path: str, **parameters: Any):
        self.path: str = path
        self.method: str = method

        url = f"{self.BASE}{self.path}"
        if parameters:
            url = url.format_map({k: _uriquote(v) if isinstance(v, str) else v for k, v in parameters.items()})
        self.url: str = url

        self.channel_id: Optional["Snowflake_Type"] = parameters.get("channel_id")
        self.guild_id: Optional["Snowflake_Type"] = parameters.get("guild_id")
        self.webhook_id: Optional["Snowflake_Type"] = parameters.get("webhook_id")
        self.webhook_token: Optional[str] = parameters.get("webhook_token")

    @property
    def rl_bucket(self):
        return f"{self.channel_id}:{self.guild_id}:{self.path}"
