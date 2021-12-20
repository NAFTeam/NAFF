import asyncio
import logging
from io import IOBase
from pathlib import Path
from typing import TYPE_CHECKING, Dict, List, Optional, Union

import attr
from aiohttp import FormData

from dis_snek.const import MISSING, logger_name
from dis_snek.errors import AlreadyDeferred
from dis_snek.mixins.send import SendMixin
from dis_snek.models.application_commands import CallbackTypes, OptionTypes
from dis_snek.models.discord_objects.message import process_message_payload
from dis_snek.models.enums import MessageFlags
from dis_snek.utils.attr_utils import define, docs
from dis_snek.models.snowflake import to_optional_snowflake, to_snowflake
from dis_snek.utils.input_utils import get_args

if TYPE_CHECKING:
    from dis_snek.client import Snake
    from dis_snek.models import File
    from dis_snek.models.discord_objects.channel import TYPE_MESSAGEABLE_CHANNEL
    from dis_snek.models.discord_objects.components import ActionRow, BaseComponent
    from dis_snek.models.discord_objects.embed import Embed
    from dis_snek.models.discord_objects.guild import Guild
    from dis_snek.models.discord_objects.message import AllowedMentions, Message
    from dis_snek.models.discord_objects.user import User, Member
    from dis_snek.models.snowflake import Snowflake_Type
    from dis_snek.models.discord_objects.message import MessageReference
    from dis_snek.models.discord_objects.sticker import Sticker
    from dis_snek.models.discord_objects.role import Role

log = logging.getLogger(logger_name)


@attr.s
class Resolved:
    """Represents resolved data in an interaction"""

    channels: Dict["Snowflake_Type", "TYPE_MESSAGEABLE_CHANNEL"] = attr.ib(
        factory=dict, metadata=docs("A dictionary of channels mentioned in the interaction")
    )
    members: Dict["Snowflake_Type", "Member"] = attr.ib(
        factory=dict, metadata=docs("A dictionary of members mentioned in the interaction")
    )
    users: Dict["Snowflake_Type", "User"] = attr.ib(
        factory=dict, metadata=docs("A dictionary of users mentioned in the interaction")
    )
    roles: Dict["Snowflake_Type", "Role"] = attr.ib(
        factory=dict, metadata=docs("A dictionary of roles mentioned in the interaction")
    )

    @classmethod
    def from_dict(cls, client: "Snake", data: dict, guild_id: Optional["Snowflake_Type"] = None):
        new_cls = cls()

        if channels := data.get("channels"):
            for key, _channel in channels.items():
                new_cls.channels[key] = client.cache.place_channel_data(_channel)

        if members := data.get("members"):
            for key, _member in members.items():
                new_cls.members[key] = client.cache.place_member_data(
                    guild_id, {**_member, "user": {**data["users"][key]}}
                )

        if users := data.get("users"):
            for key, _user in users.items():
                new_cls.users[key] = client.cache.place_user_data(_user)

        if roles := data.get("roles"):
            for key, _role in roles.items():
                new_cls.roles[key] = client.cache.role_cache.get(to_snowflake(key))

        return new_cls


@define
class Context:
    """Represents the context of a command"""

    _client: "Snake" = attr.ib(default=None)
    invoked_name: str = attr.ib(default=None, metadata=docs("The name of the command to be invoked"))

    args: List = attr.ib(factory=list, metadata=docs("The list of arguments to be passed to the command"))
    kwargs: Dict = attr.ib(factory=dict, metadata=docs("The list of keyword arguments to be passed"))

    author: Union["Member", "User"] = attr.ib(default=None, metadata=docs("The author of the message"))
    channel: "TYPE_MESSAGEABLE_CHANNEL" = attr.ib(default=None, metadata=docs("The channel this was sent within"))
    guild_id: "Snowflake_Type" = attr.ib(
        default=None, converter=to_optional_snowflake, metadata=docs("The guild this was sent within, if not a DM")
    )
    message: "Message" = attr.ib(default=None, metadata=docs("The message associated with this context"))

    @property
    def guild(self) -> Optional["Guild"]:
        return self._client.cache.guild_cache.get(self.guild_id)

    @property
    def bot(self) -> "Snake":
        """A reference to the bot instance"""
        return self._client


@define
class _BaseInteractionContext(Context):
    """An internal object used to define the attributes of interaction context and its children"""

    _token: str = attr.ib(default=None, metadata=docs("The token for the interaction"))
    interaction_id: str = attr.ib(default=None, metadata=docs("The id of the interaction"))
    target_id: "Snowflake_Type" = attr.ib(
        default=None, metadata=docs("The ID of the target, used for context menus to show what was clicked on")
    )

    deferred: bool = attr.ib(default=False, metadata=docs("Is this interaction deferred?"))
    responded: bool = attr.ib(default=False, metadata=docs("Have we responded to the interaction?"))
    ephemeral: bool = attr.ib(default=False, metadata=docs("Are responses to this interaction *hidden*"))

    resolved: Resolved = attr.ib(default=Resolved(), metadata=docs("Discord objects mentioned within this interaction"))

    data: Dict = attr.ib(factory=dict, metadata=docs("The raw data of this interaction"))

    @classmethod
    def from_dict(cls, data: Dict, client: "Snake"):
        """Create a context object from a dictionary"""
        new_cls = cls(
            client=client,
            token=data["token"],
            interaction_id=data["id"],
            data=data,
            invoked_name=data["data"].get("name"),
            guild_id=data.get("guild_id"),
        )
        new_cls.data = data

        if res_data := data["data"].get("resolved"):
            new_cls.resolved = Resolved.from_dict(client, res_data, new_cls.guild_id)

        if new_cls.guild_id:
            new_cls.author = client.cache.place_member_data(new_cls.guild_id, data["member"].copy())
            client.cache.place_user_data(data["member"]["user"])
            new_cls.channel = client.cache.channel_cache.get(to_snowflake(data["channel_id"]))
        else:
            new_cls.author = client.cache.place_user_data(data["user"])
            new_cls.channel = client.cache.channel_cache.get(new_cls.author.id)

        new_cls.target_id = data["data"].get("target_id")

        new_cls._process_options(data)

        return new_cls

    def _process_options(self, data: dict):
        kwargs = {}
        if options := data["data"].get("options"):
            o_type = options[0]["type"]
            if o_type in (OptionTypes.SUB_COMMAND, OptionTypes.SUB_COMMAND_GROUP):
                # this is a subcommand, process accordingly
                if o_type == OptionTypes.SUB_COMMAND:
                    self.invoked_name = f"{self.invoked_name} {options[0]['name']}"
                    options = options[0].get("options", [])
                else:
                    self.invoked_name = (
                        f"{self.invoked_name} {options[0]['name']} "
                        f"{next(x for x in options[0]['options'] if x['type'] == OptionTypes.SUB_COMMAND)['name']}"
                    )
                    options = options[0]["options"][0].get("options", [])

            for option in options:
                value = option.get("value")

                # this block here resolves the options using the cache
                match option["type"]:
                    case OptionTypes.USER:
                        value = (
                            self._client.cache.member_cache.get(
                                (to_snowflake(data.get("guild_id", 0)), to_snowflake(value))
                            )
                            or self._client.cache.user_cache.get(to_snowflake(value))
                        ) or value

                    case OptionTypes.CHANNEL:
                        value = self._client.cache.channel_cache.get(to_snowflake(value)) or value

                    case OptionTypes.ROLE:
                        value = self._client.cache.role_cache.get(to_snowflake(value)) or value

                    case OptionTypes.MENTIONABLE:
                        snow = to_snowflake(value)
                        if user := self._client.cache.member_cache.get(snow) or self._client.cache.user_cache.get(snow):
                            value = user
                        elif role := self._client.cache.role_cache.get(snow):
                            value = role

                if option.get("focused", False):
                    self.focussed_option = option.get("name")
                kwargs[option["name"].lower()] = value
        self.kwargs = kwargs
        self.args = [v for v in kwargs.values()]


@define
class InteractionContext(_BaseInteractionContext, SendMixin):
    """
    Represents the context of an interaction

    !!! info "Ephemeral messages:"
        Ephemeral messages allow you to send messages that only the author of the interaction can see.
        They are best considered as `fire-and-forget`, in the sense that you cannot edit them once they have been sent.

        Should you attach a component (ie. button) to the ephemeral message,
        you will be able to edit it when responding to a button interaction.
    """

    async def defer(self, ephemeral=False) -> None:
        """
        Defers the response, showing a loading state.

        parameters:
            ephemeral: Should the response be ephemeral
        """
        if self.deferred or self.responded:
            raise AlreadyDeferred("You have already responded to this interaction!")

        payload = {"type": CallbackTypes.DEFERRED_CHANNEL_MESSAGE_WITH_SOURCE}
        if ephemeral:
            payload["data"] = {"flags": MessageFlags.EPHEMERAL}

        await self._client.http.post_initial_response(payload, self.interaction_id, self._token)
        self.ephemeral = ephemeral
        self.deferred = True

    async def _send_http_request(self, message_payload: Union[dict, "FormData"]) -> dict:
        if self.responded:
            message_data = await self._client.http.post_followup(message_payload, self._client.app.id, self._token)
        else:
            if isinstance(message_payload, FormData) and not self.deferred:
                await self.defer()
            if self.deferred:
                message_data = await self._client.http.edit_interaction_message(
                    message_payload, self._client.app.id, self._token
                )
                self.deferred = False
            else:
                payload = {"type": CallbackTypes.CHANNEL_MESSAGE_WITH_SOURCE, "data": message_payload}
                await self._client.http.post_initial_response(payload, self.interaction_id, self._token)
                message_data = await self._client.http.get_interaction_message(self._client.app.id, self._token)
            self.responded = True

        return message_data

    async def send(
        self,
        content: Optional[str] = None,
        embeds: Optional[Union[List[Union["Embed", dict]], Union["Embed", dict]]] = None,
        embed: Optional[Union["Embed", dict]] = None,
        components: Optional[
            Union[List[List[Union["BaseComponent", dict]]], List[Union["BaseComponent", dict]], "BaseComponent", dict]
        ] = None,
        stickers: Optional[Union[List[Union["Sticker", "Snowflake_Type"]], "Sticker", "Snowflake_Type"]] = None,
        allowed_mentions: Optional[Union["AllowedMentions", dict]] = None,
        reply_to: Optional[Union["MessageReference", "Message", dict, "Snowflake_Type"]] = None,
        file: Optional[Union["File", "IOBase", "Path", str]] = None,
        tts: bool = False,
        flags: Optional[Union[int, "MessageFlags"]] = None,
        ephemeral: bool = False,
    ) -> "Message":
        """
        Send a message.

        parameters:
            content: Message text content.
            embeds: Embedded rich content (up to 6000 characters).
            embed: Embedded rich content (up to 6000 characters).
            components: The components to include with the message.
            stickers: IDs of up to 3 stickers in the server to send in the message.
            allowed_mentions: Allowed mentions for the message.
            reply_to: Message to reference, must be from the same channel.
            file: Location of file to send, the bytes or the File() instance, defaults to None.
            tts: Should this message use Text To Speech.
            flags: Message flags to apply.
            ephemeral bool: Should this message be sent as ephemeral (hidden)

        returns:
            New message object that was sent.
        """
        if ephemeral:
            flags = MessageFlags.EPHEMERAL

        return await super().send(
            content,
            embeds=embeds,
            embed=embed,
            components=components,
            stickers=stickers,
            allowed_mentions=allowed_mentions,
            tts=tts,
            flags=flags,
        )


@define
class ComponentContext(InteractionContext):
    custom_id: str = attr.ib(default="", metadata=docs("The ID given to the component that has been pressed"))
    component_type: int = attr.ib(default=0, metadata=docs("The type of component that has been pressed"))

    values: List = attr.ib(factory=list, metadata=docs("The values set"))

    defer_edit_origin: bool = attr.ib(default=False, metadata=docs("Are we editing the message the component is on"))

    @classmethod
    def from_dict(cls, data: Dict, client: "Snake") -> "ComponentContext":
        """Create a context object from a dictionary"""
        new_cls = super().from_dict(data, client)
        new_cls.token = data["token"]
        new_cls.interaction_id = data["id"]
        new_cls.custom_id = data["data"]["custom_id"]
        new_cls.component_type = data["data"]["component_type"]
        new_cls.message = client.cache.place_message_data(data["message"])
        new_cls.values = data["data"].get("values", [])

        return new_cls

    async def defer(self, ephemeral=False, edit_origin: bool = False) -> None:
        """
        Defers the response, showing a loading state.

        parameters:
            ephemeral: Should the response be ephemeral
            edit_origin: Whether we intend to edit the original message
        """
        if self.deferred or self.responded:
            raise AlreadyDeferred("You have already responded to this interaction!")

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
        embeds: Optional[Union[List[Union["Embed", dict]], Union["Embed", dict]]] = None,
        embed: Optional[Union["Embed", dict]] = None,
        components: Optional[
            Union[List[List[Union["BaseComponent", dict]]], List[Union["BaseComponent", dict]], "BaseComponent", dict]
        ] = None,
        allowed_mentions: Optional[Union["AllowedMentions", dict]] = None,
        file: Optional[Union["File", "IOBase", "Path", str]] = None,
        tts: bool = False,
    ) -> "Message":
        """
        Edits the original message of the component.

        parameters:
            content: Message text content.
            embeds: Embedded rich content (up to 6000 characters).
            embed: Embedded rich content (up to 6000 characters).
            components: The components to include with the message.
            allowed_mentions: Allowed mentions for the message.
            reply_to: Message to reference, must be from the same channel.
            file: Location of file to send, the bytes or the File() instance, defaults to None.
            tts: Should this message use Text To Speech.

        returns:
            The message after it was edited.
        """
        if not self.responded and not self.deferred and file:
            # Discord doesn't allow files at initial response, so we defer then edit.
            await self.defer(edit_origin=True)

        message_payload = process_message_payload(
            content=content,
            embeds=embeds or embed,
            components=components,
            allowed_mentions=allowed_mentions,
            file=file,
            tts=tts,
        )

        message_data = None
        if self.deferred:
            if not self.defer_edit_origin:
                log.warning(
                    "If you want to edit the original message, and need to defer, you must set the `edit_origin` kwarg to True!"
                )

            message_data = await self._client.http.edit_interaction_message(
                message_payload, self._client.app.id, self._token
            )
            self.deferred = False
            self.defer_edit_origin = False
        else:
            payload = {"type": CallbackTypes.UPDATE_MESSAGE, "data": message_payload}
            await self._client.http.post_initial_response(payload, self.interaction_id, self._token)
            message_data = await self._client.http.get_interaction_message(self._client.app.id, self._token)

        if message_data:
            self.message = self._client.cache.place_message_data(message_data)
            return self.message


@define
class AutocompleteContext(_BaseInteractionContext):
    focussed_option: str = attr.ib(default=MISSING, metadata=docs("The option the user is currently filling in"))

    @classmethod
    def from_dict(cls, data: Dict, client: "Snake") -> "ComponentContext":
        """Create a context object from a dictionary"""
        new_cls = super().from_dict(data, client)

        return new_cls

    @property
    def input_text(self) -> str:
        """The text the user has entered so far"""
        return self.kwargs.get(self.focussed_option, "")

    async def send(self, choices: List[Union[str, int, float, Dict[str, Union[str, int, float]]]]):
        """
        Send your autocomplete choices to discord.
        Choices must be either a list of strings, or a dictionary following the following format:

        ```json
            {
              "name": str,
              "value": str
            }
        ```
        Where name is the text visible in Discord, and value is the data sent back to your client when that choice is
        chosen.

        Args:
            choices: 25 choices the user can pick
        """
        processed_choices = []
        for choice in choices:
            if isinstance(choice, (int, float)):
                processed_choices.append({"name": str(choice), "value": choice})
            elif isinstance(choice, dict):
                processed_choices.append(choice)
            else:
                choice = str(choice)
                processed_choices.append({"name": choice, "value": choice.replace(" ", "_")})

        payload = {"type": CallbackTypes.AUTOCOMPLETE_RESULT, "data": {"choices": processed_choices}}
        await self._client.http.post_initial_response(payload, self.interaction_id, self._token)


@define
class MessageContext(Context, SendMixin):
    prefix: str = attr.ib(default=MISSING, metadata=docs("The prefix used to invoke this command"))

    @classmethod
    def from_message(cls, client: "Snake", message: "Message"):
        new_cls = cls(
            client=client,
            message=message,
            author=message.author,
            channel=message.channel,
            guild_id=message.guild.id if message.guild else None,
        )
        return new_cls

    @property
    def content_parameters(self) -> str:
        return self.message.content.removeprefix(f"{self.prefix}{self.invoked_name}").strip()

    async def _send_http_request(self, message_payload: Union[dict, "FormData"]) -> dict:
        return await self._client.http.create_message(message_payload, self.channel.id)
