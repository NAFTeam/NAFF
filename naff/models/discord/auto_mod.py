import logging
from typing import TYPE_CHECKING, Union

from naff.client.const import logger_name, MISSING
from naff.client.utils.attr_utils import define, field
from naff.models.discord.base import ClientObject
from naff.models.discord.enums import AutoModTriggerType, AutoModAction

if TYPE_CHECKING:
    from naff import Snowflake_Type, Guild, GuildText, Message, Client

__all__ = ("AutoModerationAction",)

log = logging.getLogger(logger_name)


@define()
class BaseAction(ClientObject):
    _type: AutoModAction = field(converter=AutoModAction)

    @classmethod
    def from_dict_factory(cls, data: dict, client: "Client") -> "BaseAction":
        action_class = ACTION_MAPPING.get(data.get("type"))
        if not action_class:
            log.error(f"Unknown action type for {data}")
            action_class = cls

        return action_class.from_dict({"type": data.get("type")} | data["metadata"], client)


@define()
class AutoModerationAction(ClientObject):
    rule_trigger_type: AutoModTriggerType = field(converter=AutoModTriggerType)
    rule_id: "Snowflake_Type" = field()

    action: BaseAction = field(default=MISSING, repr=True)

    matched_keyword: str = field(repr=True)
    matched_content: str = field()
    content: str = field()

    _message_id: Union["Snowflake_Type", None] = field(default=None)
    _alert_system_message_id: "Snowflake_Type" = field()
    _channel_id: "Snowflake_Type" = field()
    _guild_id: "Snowflake_Type" = field()

    @classmethod
    def _process_dict(cls, data: dict, client: "Client") -> dict:
        data = super()._process_dict(data, client)
        data["action"] = BaseAction.from_dict_factory(data["action"], client)
        return data

    @property
    def guild(self) -> "Guild":
        return self._client.get_guild(self._guild_id)

    @property
    def channel(self) -> "GuildText":
        return self._client.get_channel(self._channel_id)

    @property
    def message(self) -> "Message":
        return self._client.cache.get_message(self._channel_id, self._message_id)


@define()
class BlockMessage(BaseAction):
    ...


@define()
class AlertMessage(BaseAction):
    _channel_id: "Snowflake_Type" = field(repr=True)

    @property
    def channel(self) -> "GuildText":
        return self._client.get_channel(self._channel_id)


@define()
class TimeoutUser(BaseAction):
    duration_seconds: int = field(repr=True)


ACTION_MAPPING = {
    AutoModAction.BLOCK_MESSAGE: BlockMessage,
    AutoModAction.ALERT_MESSAGE: AlertMessage,
    AutoModAction.TIMEOUT_USER: TimeoutUser,
}
