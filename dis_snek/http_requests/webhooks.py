from typing import TYPE_CHECKING, Any

from dis_snek.models.route import Route

if TYPE_CHECKING:
    from dis_snek.models.snowflake import Snowflake_Type


class WebhookRequests:
    request: Any
