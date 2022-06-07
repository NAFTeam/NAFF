import logging
from typing import TYPE_CHECKING, Union, Any


from naff.client.const import logger_name, MISSING
from naff.client.mixins.serialization import DictSerializationMixin
from naff.client.utils import list_converter, no_export_meta
from naff.client.utils.attr_utils import define, field, docs
from naff.models.discord.base import ClientObject, DiscordObject
from naff.models.discord.enums import AutoModTriggerType, AutoModAction, AutoModEvent, AutoModLanuguageType

if TYPE_CHECKING:
    from naff import Snowflake_Type, Guild, GuildText, Message, Client, Member

__all__ = ("AutoModerationAction", "AutoModRule")

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
class BaseTrigger(DictSerializationMixin):
    type: AutoModTriggerType = field(converter=AutoModTriggerType, repr=True, metadata=docs("The type of trigger"))
    _trigger_metadata: dict = field(metadata=no_export_meta | docs("The raw metadata of this trigger (for debugging)"))

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

    def to_dict(self) -> dict:
        data = super().to_dict()
        data["trigger_metadata"] = {k: data.pop(k) for k, v in data.copy().items() if k != "type"}
        data["trigger_type"] = data.pop("type")
        return data


@define()
class KeywordTrigger(BaseTrigger):
    keyword_filter: list[str] = field(factory=list, repr=True, metadata=docs("What words will trigger this"))


@define()
class HarmfulLinkFilter(BaseTrigger):
    ...


@define()
class KeywordPresetTrigger(BaseTrigger):
    keyword_lists: list[AutoModLanuguageType] = field(
        factory=list,
        converter=list_converter(AutoModLanuguageType),
        repr=True,
        metadata=docs("The preset list of keywords that will trigger this"),
    )


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


@define()
class AutoModRule(DiscordObject):
    name: str = field()
    enabled: bool = field(default=False)

    actions: list[BaseAction] = field(factory=list)
    event_type: AutoModEvent = field()
    trigger: BaseTrigger = field()
    exempt_roles: list["Snowflake_Type"] = field(factory=list)
    exempt_channels: list["Snowflake_Type"] = field(factory=list)

    _guild_id: "Snowflake_Type" = field()
    _creator_id: "Snowflake_Type" = field()

    @classmethod
    def _process_dict(cls, data: dict, client: "Client") -> dict:
        data = super()._process_dict(data, client)
        data["actions"] = [BaseAction.from_dict_factory(d, client) for d in data["actions"]]
        data["trigger"] = BaseTrigger.from_dict_factory(data)
        return data

    @property
    def creator(self) -> "Member":
        return self._client.cache.get_member(self._guild_id, self._creator_id)

    @property
    def guild(self) -> "Guild":
        return self._client.cache.get_guild(self._guild_id)


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
