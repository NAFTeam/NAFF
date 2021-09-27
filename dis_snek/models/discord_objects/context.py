from functools import partial
from pathlib import Path
from typing import TYPE_CHECKING, Dict, List, Optional, Union, Awaitable

import attr
from aiohttp import FormData

from dis_snek.mixins.send import SendMixin
from dis_snek.models.application_commands import CallbackTypes
from dis_snek.models.discord_objects.message import process_message_payload
from dis_snek.models.enums import MessageFlags
from dis_snek.utils.proxy import CacheProxy

if TYPE_CHECKING:
    from dis_snek.client import Snake
    from dis_snek.models.discord_objects.channel import TYPE_MESSAGEABLE_CHANNEL
    from dis_snek.models.discord_objects.components import ActionRow
    from dis_snek.models.discord_objects.embed import Embed
    from dis_snek.models.discord_objects.guild import Guild
    from dis_snek.models.discord_objects.message import AllowedMentions, Message
    from dis_snek.models.discord_objects.user import User, Member
    from dis_snek.models.snowflake import Snowflake_Type


@attr.s
class Context:
    """
    Represents the context of a command

    Attributes:
        message Message: The message associated with this context
        invoked_name str: The name of the command to be invoked
        author User: The author of the message
        channel Channel: The channel this was sent within
        guild Guild: The guild this was sent within, if not a DM
        args list: The list of arguments to be passed to the command
        kwargs dict: The list of keyword arguments to be passed

    """

    _client: "Snake" = attr.ib(default=None)
    message: "Message" = attr.ib(default=None)
    invoked_name: str = attr.ib(default=None)

    args: List = attr.ib(factory=list)

    kwargs: Dict = attr.ib(factory=dict)

    author: Union[CacheProxy, Awaitable[Union["Member", "User"]], Union["Member", "User"]] = attr.ib(default=None)
    channel: Union[CacheProxy, Awaitable["TYPE_MESSAGEABLE_CHANNEL"], "TYPE_MESSAGEABLE_CHANNEL"] = attr.ib(
        default=None
    )
    guild: Optional[Union[CacheProxy, Awaitable["Guild"], "Guild"]] = attr.ib(default=None)

    @property
    def bot(self):
        """A reference to the bot instance"""
        return self._client


@attr.s
class InteractionContext(Context, SendMixin):
    """
    Represents the context of an interaction

    !!! info "Ephemeral messages:"
        Ephemeral messages allow you to send messages that only the author of the interaction can see.
        They are best considered as `fire-and-forget`, in the sense that you cannot edit them once they have been sent.

        Should you attach a component (ie. button) to the ephemeral message,
        you will be able to edit it when responding to a button interaction.

    Attributes:
        interaction_id str: The id of the interaction
        target_id Snowflake_Type: The ID of the target, used for context menus to show what was clicked on
        deferred bool: Is this interaction deferred?
        responded bool: Have we responded to the interaction?
        ephemeral bool: Are responses to this interaction *hidden*
        resolved dict: A dictionary of discord objects mentioned within this interaction
        data dict: The raw data of this interaction
    """

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

        parameters:
            ephemeral: Should the response be ephemeral
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

    async def send(
        self,
        content: Optional[str] = None,
        embeds: Optional[Union[List[Union["Embed", dict]], Union["Embed", dict]]] = None,
        components: Optional[
            Union[List[List[Union["BaseComponent", dict]]], List[Union["BaseComponent", dict]], "BaseComponent", dict]
        ] = None,
        stickers: Optional[Union[List[Union["Sticker", "Snowflake_Type"]], "Sticker", "Snowflake_Type"]] = None,
        allowed_mentions: Optional[Union["AllowedMentions", dict]] = None,
        reply_to: Optional[Union["MessageReference", "Message", dict, "Snowflake_Type"]] = None,
        filepath: Optional[Union[str, "Path"]] = None,
        tts: bool = False,
        flags: Optional[Union[int, "MessageFlags"]] = None,
        ephemeral: bool = False,
    ) -> "Message":
        """
        Send a message.

        parameters:
            content: Message text content.
            embeds: Embedded rich content (up to 6000 characters).
            components: The components to include with the message.
            stickers: IDs of up to 3 stickers in the server to send in the message.
            allowed_mentions: Allowed mentions for the message.
            reply_to: Message to reference, must be from the same channel.
            filepath: Location of file to send, defaults to None.
            tts: Should this message use Text To Speech.
            flags: Message flags to apply.
            ephemeral bool: Should this message be sent as ephemeral (hidden)

        returns:
            New message object that was sent.
        """
        if ephemeral:
            flags = MessageFlags.EPHEMERAL

        return await super().send(
            content, embeds, components, stickers, allowed_mentions, reply_to, filepath, tts, flags
        )


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

        parameters:
            ephemeral: Should the response be ephemeral
            edit_origin: Whether we intend to edit the original message
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

        parameters:
            content: Message text content.
            embeds: Embedded rich content (up to 6000 characters).
            components: The components to include with the message.
            allowed_mentions: Allowed mentions for the message.
            reply_to: Message to reference, must be from the same channel.
            filepath: Location of file to send, defaults to None.
            tts: Should this message use Text To Speech.

        returns:
            The message after it was edited.
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
