from pathlib import Path
from typing import TYPE_CHECKING, Dict, List, Optional, Union

import attr
from dis_snek.models.discord_objects.interactions import CallbackTypes
from dis_snek.models.discord_objects.message import process_message_payload
from dis_snek.models.enums import MessageFlags

if TYPE_CHECKING:
    from dis_snek.client import Snake
    from dis_snek.models.discord_objects.channel import BaseChannel
    from dis_snek.models.discord_objects.components import ActionRow, BaseComponent
    from dis_snek.models.discord_objects.embed import Embed
    from dis_snek.models.discord_objects.guild import Guild
    from dis_snek.models.discord_objects.message import AllowedMentions, Message, MessageReference
    from dis_snek.models.discord_objects.sticker import Sticker
    from dis_snek.models.discord_objects.user import User
    from dis_snek.models.snowflake import Snowflake_Type


@attr.s
class Context:
    """Represents the context of a command"""

    _client: "Snake" = attr.ib(default=None)
    message: "Message" = attr.ib(default=None)

    args: List = attr.ib(factory=list)
    kwargs: Dict = attr.ib(factory=dict)

    author: "User" = attr.ib(default=None)
    channel: "BaseChannel" = attr.ib(default=None)
    guild: "Guild" = attr.ib(default=None)


@attr.s
class InteractionContext(Context):
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
        return cls(client=client, token=data["token"], interaction_id=data["id"], data=data)

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
        filepath: Optional[Union[str, Path]] = None,
        tts: bool = False,
        flags: Optional[Union[int, MessageFlags]] = None,
    ) -> "Message":
        """
        Send a message.

        :param content: Message text content.
        :param embeds: Embedded rich content (up to 6000 characters).
        :param components: The components to include with the message.
        :param stickers: IDs of up to 3 stickers in the server to send in the message.
        :param allowed_mentions: Allowed mentions for the message.
        :param reply_to: Message to reference, must be from the same channel.
        :param filepath: Location of file to send, defaults to None.
        :param tts: Should this message use Text To Speech.

        :return: New message object that was sent.
        """
        if not self.responded and not self.deferred and (filepath or stickers):
            # Discord doesn't allow files at initial response, so we defer then edit.
            await self.defer()

        message_payload = process_message_payload(
            content=content,
            embeds=embeds,
            components=components,
            stickers=stickers,
            allowed_mentions=allowed_mentions,
            reply_to=reply_to,
            filepath=filepath,
            tts=tts,
            flags=flags,
        )

        message_data = None
        if self.responded:
            message_data = await self._client.http.post_followup(message_payload, self._client.user.id, self._token)
        else:
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

        if message_data:
            self.message = self._client.cache.place_message_data(message_data)
            return self.message


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
