import logging
from typing import TYPE_CHECKING, Union, Any

import attrs

from naff.client.const import logger_name, MISSING, Absent
from naff.client.mixins.serialization import DictSerializationMixin
from naff.client.utils import list_converter
from naff.client.utils.attr_utils import define, field, docs
from naff.models.discord.base import ClientObject, DiscordObject
from naff.models.discord.enums import AutoModTriggerType, AutoModAction, AutoModEvent, AutoModLanuguageType
from naff.models.discord.snowflake import to_snowflake_list

if TYPE_CHECKING:
    from naff import (
        Snowflake_Type,
        Guild,
        GuildText,
        Message,
        Client,
        Member,
    )

__all__ = ("AutoModerationAction", "AutoModRule")

log = logging.getLogger(logger_name)


@define()
class BaseAction(DictSerializationMixin):
    type: AutoModAction = field(converter=AutoModAction)

    @classmethod
    def from_dict_factory(cls, data: dict) -> "BaseAction":
        action_class = ACTION_MAPPING.get(data.get("type"))
        if not action_class:
            log.error(f"Unknown action type for {data}")
            action_class = cls

        return action_class.from_dict({"type": data.get("type")} | data["metadata"])

    def as_dict(self) -> dict:
        data = attrs.asdict(self)
        data["metadata"] = {k: data.pop(k) for k, v in data.copy().items() if k != "type"}
        return data


@define()
class BaseTrigger(DictSerializationMixin):
    type: AutoModTriggerType = field(converter=AutoModTriggerType, repr=True, metadata=docs("The type of trigger"))

    @classmethod
    def _process_dict(cls, data: dict[str, Any]) -> dict[str, Any]:
        data = super()._process_dict(data)

        if meta := data.get("trigger_metadata"):
            for key, val in meta.items():
                data[key] = val

        return data

    @classmethod
    def from_dict_factory(cls, data: dict) -> "BaseAction":
        trigger_class = TRIGGER_MAPPING.get(data.get("trigger_type"))
        meta = data.get("trigger_metadata", {})
        if not trigger_class:
            log.error(f"Unknown trigger type for {data}")
            trigger_class = cls

        payload = {"type": data.get("trigger_type"), "trigger_metadata": meta}

        return trigger_class.from_dict(payload)

    def as_dict(self) -> dict:
        data = attrs.asdict(self)
        data["trigger_metadata"] = {k: data.pop(k) for k, v in data.copy().items() if k != "type"}
        data["trigger_type"] = data.pop("type")
        return data


@define()
class KeywordTrigger(BaseTrigger):
    type: AutoModTriggerType = field(
        default=AutoModTriggerType.KEYWORD,
        converter=AutoModTriggerType,
        repr=True,
        metadata=docs("The type of trigger"),
    )
    keyword_filter: list[str] = field(factory=list, repr=True, metadata=docs("What words will trigger this"))


@define()
class HarmfulLinkFilter(BaseTrigger):
    type: AutoModTriggerType = field(
        default=AutoModTriggerType.HARMFUL_LINK,
        converter=AutoModTriggerType,
        repr=True,
        metadata=docs("The type of trigger"),
    )
    ...


@define()
class KeywordPresetTrigger(BaseTrigger):
    type: AutoModTriggerType = field(
        default=AutoModTriggerType.KEYWORD_PRESET,
        converter=AutoModTriggerType,
        repr=True,
        metadata=docs("The type of trigger"),
    )
    keyword_lists: list[AutoModLanuguageType] = field(
        factory=list,
        converter=list_converter(AutoModLanuguageType),
        repr=True,
        metadata=docs("The preset list of keywords that will trigger this"),
    )


@define()
class BlockMessage(BaseAction):
    type: AutoModAction = field(default=AutoModAction.BLOCK_MESSAGE, converter=AutoModAction)
    ...


@define()
class AlertMessage(BaseAction):
    channel_id: "Snowflake_Type" = field(repr=True)
    type: AutoModAction = field(default=AutoModAction.ALERT_MESSAGE, converter=AutoModAction)


@define(kw_only=False)
class TimeoutUser(BaseAction):
    duration_seconds: int = field(repr=True, default=60)
    type: AutoModAction = field(default=AutoModAction.TIMEOUT_USER, converter=AutoModAction)


@define()
class AutoModRule(DiscordObject):
    name: str = field()
    enabled: bool = field(default=False)

    actions: list[BaseAction] = field(factory=list)
    event_type: AutoModEvent = field()
    trigger: BaseTrigger = field()
    exempt_roles: list["Snowflake_Type"] = field(factory=list, converter=to_snowflake_list)
    exempt_channels: list["Snowflake_Type"] = field(factory=list, converter=to_snowflake_list)

    _guild_id: "Snowflake_Type" = field(default=MISSING)
    _creator_id: "Snowflake_Type" = field(default=MISSING)
    id: "Snowflake_Type" = field(default=MISSING)

    @classmethod
    def _process_dict(cls, data: dict, client: "Client") -> dict:
        data = super()._process_dict(data, client)
        data["actions"] = [BaseAction.from_dict_factory(d) for d in data["actions"]]
        data["trigger"] = BaseTrigger.from_dict_factory(data)
        return data

    def to_dict(self) -> dict:
        data = super().to_dict()
        trigger = data.pop("trigger")
        data["trigger_type"] = trigger["trigger_type"]
        data["trigger_metadata"] = trigger["trigger_metadata"]
        return data

    @property
    def creator(self) -> "Member":
        return self._client.cache.get_member(self._guild_id, self._creator_id)

    @property
    def guild(self) -> "Guild":
        return self._client.cache.get_guild(self._guild_id)

    async def delete(self, reason: Absent[str] = MISSING) -> None:
        """
        Delete this rule

        Args:
            reason: The reason for deleting this rule
        """
        await self._client.http.delete_auto_moderation_rule(self._guild_id, self.id, reason=reason)


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


ACTION_MAPPING = {
    AutoModAction.BLOCK_MESSAGE: BlockMessage,
    AutoModAction.ALERT_MESSAGE: AlertMessage,
    AutoModAction.TIMEOUT_USER: TimeoutUser,
}

TRIGGER_MAPPING = {
    AutoModTriggerType.KEYWORD: KeywordTrigger,
    AutoModTriggerType.HARMFUL_LINK: HarmfulLinkFilter,
    AutoModTriggerType.KEYWORD_PRESET: KeywordPresetTrigger,
}
