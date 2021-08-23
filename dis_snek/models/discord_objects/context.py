from aiohttp.formdata import FormData
from dis_snek.mixins.send import SendMixin
from dis_snek.models.enums import MessageFlags
from dis_snek.models.discord_objects.interactions import CallbackTypes
from typing import TYPE_CHECKING, Any, Dict, List, Union

import attr

from dis_snek.models.discord_objects.channel import BaseChannel
from dis_snek.models.discord_objects.components import ActionRow, process_components
from dis_snek.models.discord_objects.embed import Embed
from dis_snek.models.discord_objects.guild import Guild
from dis_snek.models.discord_objects.message import Message
from dis_snek.models.discord_objects.user import User
from dis_snek.models.snowflake import Snowflake_Type

if TYPE_CHECKING:
    from dis_snek.client import Snake


@attr.s
class Context:
    """Represents the context of a command"""

    _client: "Snake" = attr.ib(default=None)
    message: Message = attr.ib(default=None)

    args: List = attr.ib(factory=list)
    kwargs: Dict = attr.ib(factory=dict)

    author: User = attr.ib(default=None)
    channel: BaseChannel = attr.ib(default=None)
    guild: Guild = attr.ib(default=None)


@attr.s
class InteractionContext(Context, SendMixin):
    """Represents the context of an interaction"""

    _token: str = attr.ib(default=None)
    interaction_id: str = attr.ib(default=None)
    target_id: Snowflake_Type = attr.ib(default=None)

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

    async def _send_http_request(self, message: Union[dict, FormData]) -> dict:
        if isinstance(message, FormData):
            # Special conditions if we are sending a file.
            if self.ephemeral:
                raise ValueError("Ephemeral messages does not support sending of files.")
            if not self.responded and not self.deferred:
                # Discord doesn't allow files at initial response, so we defer then edit.
                await self.defer()

        message_data = None
        if not self.responded:
            if self.deferred:
                message_data = await self._client.http.edit_interaction_message(
                    message, self._client.user.id, self._token
                )
                self.deferred = False
            else:
                payload = {"type": CallbackTypes.CHANNEL_MESSAGE_WITH_SOURCE, "data": message}
                await self._client.http.post_initial_response(payload, self.interaction_id, self._token)
                message_data = await self._client.http.get_interaction_message(self._client.user.id, self._token)
            self.responded = True
        else:
            message_data = await self._client.http.post_followup(message, self._client.user.id, self._token)

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
        embeds: List[Embed] = None,
        tts: bool = False,
        components: List[Union[Dict, ActionRow]] = None,
    ) -> Message:
        """
        Edits the original message of the component.

        :param content: Message content
        :param embeds: List of embeds to send
        :param tts: Should this response use tts
        :param components: List of interaction components

        :return: The message after it was edited.
        """
        # TODO Not sure if this can use a mixin...

        message: Dict[str, Any] = {"tts": tts}

        if content:
            message["content"] = str(content)

        if components:
            message["components"] = process_components(components)

        if embeds:
            message["embeds"] = embeds

        message_data = None
        if self.deferred:
            message_data = await self._client.http.edit_interaction_message(message, self._client.user.id, self._token)
            self.deferred = False
            self.defer_edit_origin = False
        else:
            payload = {"type": CallbackTypes.UPDATE_MESSAGE, "data": message}
            await self._client.http.post_initial_response(payload, self.interaction_id, self._token)
            message_data = await self._client.http.get_interaction_message(self._client.user.id, self._token)

        if message_data:
            self.message = await self._client.cache.place_message_data(
                message_data["channel_id"], message_data["id"], message_data
            )
            return self.message
