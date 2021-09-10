from functools import partial
from pathlib import Path
from typing import TYPE_CHECKING, Dict, List, Optional, Union, Awaitable

import attr
from aiohttp import FormData

from dis_snek.mixins.send import SendMixin
from dis_snek.models.discord_objects.interactions import CallbackTypes
from dis_snek.models.discord_objects.message import process_message_payload
from dis_snek.models.enums import MessageFlags
from dis_snek.utils.proxy import CacheProxy

if TYPE_CHECKING:
    from dis_snek.client import Snake
    from dis_snek.models.discord_objects.channel import TextChannel
    from dis_snek.models.discord_objects.components import ActionRow
    from dis_snek.models.discord_objects.embed import Embed
    from dis_snek.models.discord_objects.guild import Guild
    from dis_snek.models.discord_objects.message import AllowedMentions, Message
    from dis_snek.models.discord_objects.user import User, Member
    from dis_snek.models.snowflake import Snowflake_Type


@attr.s
class Context:
    """Represents the context of a command"""

    _client: "Snake" = attr.ib(default=None)
    message: "Message" = attr.ib(default=None)

    invoked_name: str = attr.ib(default=None)

    args: List = attr.ib(factory=list)
    kwargs: Dict = attr.ib(factory=dict)

    author: Union[CacheProxy, Awaitable[Union["Member", "User"]], Union["Member", "User"]] = attr.ib(default=None)
    channel: Union[CacheProxy, Awaitable["TextChannel"], "TextChannel"] = attr.ib(default=None)
    guild: Optional[Union[CacheProxy, Awaitable["Guild"], "Guild"]] = attr.ib(default=None)

    @property
    def bot(self):
        return self._client


@attr.s
class InteractionContext(Context, SendMixin):
    """Represents the context of an interaction"""

    _token: str = attr.ib(default=None)
    interaction_id: str = attr.ib(default=None)
    target_id: "Snowflake_Type" = attr.ib(default=None)

    deferred: bool = attr.ib(default=False)
    responded: bool = attr.ib(default=False)
    ephemeral: bool = attr.ib(default=False)

    resolved: dict = attr.ib(factory=dict)

    data: Dict = attr.ib(factory=dict)

    @classmethod
    def from_dict(cls, data: Dict, client: "Snake") -> "InteractionContext":
        """Create a context object from a dictionary"""
        return cls(
            client=client, token=data["token"], interaction_id=data["id"], data=data, invoked_name=data["data"]["name"]
        )

    async def process_resolved(self, res_data):
        # todo: maybe a resolved dataclass instead of this?
        if channels := res_data.get("channels"):
            self.resolved["channels"] = {}
            for key, _channel in channels.items():
                self.bot.cache.place_channel_data(_channel)
                self.resolved["channels"][key] = CacheProxy(id=key, method=self.bot.cache.get_channel)

        if members := res_data.get("members"):
            self.resolved["members"] = {}
            for key, _member in members.items():
                self.bot.cache.place_member_data(self.guild.id, {**_member, "user": {**res_data["users"][key]}})
                self.resolved["members"][key] = CacheProxy(
                    id=key, method=partial(self.bot.cache.get_member, self.guild.id)
                )

        elif users := res_data.get("users"):
            self.resolved["users"] = {}
            for key, _user in users.items():
                self.bot.cache.place_user_data(_user)
                self.resolved["users"][key] = CacheProxy(id=key, method=self.bot.cache.get_user)

        if roles := res_data.get("roles"):
            self.resolved["roles"] = {}
            for key, _role in roles.items():
                self.bot.cache.place_role_data(self.guild.id, _role)
                self.resolved["roles"][key] = CacheProxy(id=key, method=self.bot.cache.get_role)

    async def defer(self, ephemeral=False) -> None:
        """
        Defers the response, showing a loading state.

        :param ephemeral: Should the response be ephemeral
        """
        if self.deferred or self.responded:
            raise Exception("You have already responded to this interaction!")

        payload = {"type": CallbackTypes.DEFERRED_CHANNEL_MESSAGE_WITH_SOURCE}
        if ephemeral:
            payload["data"] = {"flags": MessageFlags.EPHEMERAL}

        await self._client.http.post_initial_response(payload, self.interaction_id, self._token)
        self.ephemeral = ephemeral
        self.deferred = True

    async def _send_http_request(self, message_payload: Union[dict, "FormData"]) -> dict:
        if self.responded:
            message_data = await self._client.http.post_followup(message_payload, self._client.user.id, self._token)
        else:
            if isinstance(message_payload, FormData) and not self.deferred:
                await self.defer()
            if self.deferred:
                message_data = await self._client.http.edit_interaction_message(
                    message_payload, self._client.user.id, self._token
                )
                self.deferred = False
            else:
                payload = {"type": CallbackTypes.CHANNEL_MESSAGE_WITH_SOURCE, "data": message_payload}
                await self._client.http.post_initial_response(payload, self.interaction_id, self._token)
                message_data = await self._client.http.get_interaction_message(self._client.user.id, self._token)
            self.responded = True

        return message_data


@attr.s
class ComponentContext(InteractionContext):
    custom_id: str = attr.ib(default="")
    component_type: int = attr.ib(default=0)

    values: List = attr.ib(factory=list)

    defer_edit_origin: bool = attr.ib(default=False)

    @classmethod
    def from_dict(cls, data: Dict, client: "Snake") -> "ComponentContext":
        """Create a context object from a dictionary"""
        return cls(
            client=client,
            token=data["token"],
            interaction_id=data["id"],
            custom_id=data["data"]["custom_id"],
            component_type=data["data"]["component_type"],
            data=data,
        )

    async def defer(self, ephemeral=False, edit_origin: bool = False) -> None:
        """
        Defers the response, showing a loading state.

        :param ephemeral: Should the response be ephemeral
        :param edit_origin: Whether we intend to edit the original message
        """
        if self.deferred or self.responded:
            raise Exception("You have already responded to this interaction!")

        payload = {
            "type": CallbackTypes.DEFERRED_UPDATE_MESSAGE
            if edit_origin
            else CallbackTypes.DEFERRED_CHANNEL_MESSAGE_WITH_SOURCE
        }

        if ephemeral:
            if edit_origin:
                raise ValueError("`edit_origin` and `ephemeral` are mutually exclusive")
            payload["data"] = {"flags": MessageFlags.EPHEMERAL}

        await self._client.http.post_initial_response(payload, self.interaction_id, self._token)
        self.deferred = True
        self.ephemeral = ephemeral
        self.defer_edit_origin = edit_origin

    async def edit_origin(
        self,
        content: str = None,
        embeds: List["Embed"] = None,
        components: List[Union[Dict, "ActionRow"]] = None,
        allowed_mentions: Optional[Union["AllowedMentions", dict]] = None,
        filepath: Optional[Union[str, Path]] = None,
        tts: bool = False,
    ) -> "Message":
        """
        Edits the original message of the component.

        :param content: Message text content.
        :param embeds: Embedded rich content (up to 6000 characters).
        :param components: The components to include with the message.
        :param allowed_mentions: Allowed mentions for the message.
        :param reply_to: Message to reference, must be from the same channel.
        :param filepath: Location of file to send, defaults to None.
        :param tts: Should this message use Text To Speech.

        :return: The message after it was edited.
        """
        if not self.responded and not self.deferred and filepath:
            # Discord doesn't allow files at initial response, so we defer then edit.
            await self.defer(edit_origin=True)

        message_payload = process_message_payload(
            content=content,
            embeds=embeds,
            components=components,
            allowed_mentions=allowed_mentions,
            filepath=filepath,
            tts=tts,
        )

        message_data = None
        if self.deferred:
            message_data = await self._client.http.edit_interaction_message(
                message_payload, self._client.user.id, self._token
            )
            self.deferred = False
            self.defer_edit_origin = False
        else:
            payload = {"type": CallbackTypes.UPDATE_MESSAGE, "data": message_payload}
            await self._client.http.post_initial_response(payload, self.interaction_id, self._token)
            message_data = await self._client.http.get_interaction_message(self._client.user.id, self._token)

        if message_data:
            self.message = self._client.cache.place_message_data(message_data)
            return self.message


@attr.s
class MessageContext(Context, SendMixin):
    invoked_name: str = attr.ib(default=None)
    arguments: list = attr.ib(factory=list)

    async def _send_http_request(self, message_payload: Union[dict, "FormData"]) -> dict:
        return await self._client.http.create_message(message_payload, self.channel.id)
