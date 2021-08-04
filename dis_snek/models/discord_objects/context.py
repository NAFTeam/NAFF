from typing import Any, Union
from typing import Dict
from typing import List

import attr

from dis_snek.models.discord_objects.channel import BaseChannel
from dis_snek.models.discord_objects.components import ActionRow, process_components
from dis_snek.models.discord_objects.embed import Embed
from dis_snek.models.discord_objects.guild import Guild
from dis_snek.models.discord_objects.message import Message
from dis_snek.models.discord_objects.user import User
from dis_snek.models.snowflake import Snowflake_Type


@attr.s
class Context:
    """Represents the context of a command"""

    _client: Any = attr.ib(default=None)
    message: Message = attr.ib(default=None)

    args: List = attr.ib(factory=list)
    kwargs: Dict = attr.ib(factory=dict)

    author: User = attr.ib(default=None)
    channel: BaseChannel = attr.ib(default=None)
    guild: Guild = attr.ib(default=None)


@attr.s
class InteractionContext(Context):
    """Represents the context of an interaction"""

    _token: str = attr.ib(default=None)
    interaction_id: str = attr.ib(default=None)
    target_id: Snowflake_Type = attr.ib(default=None)

    deferred: bool = attr.ib(default=False)
    responded: bool = attr.ib(default=False)
    ephemeral: bool = attr.ib(default=False)

    data: Dict = attr.ib(factory=dict)

    @classmethod
    def from_dict(cls, data: Dict, client):
        """Create a context object from a dictionary"""
        return cls(client=client, token=data["token"], interaction_id=data["id"], data=data)

    async def defer(self, ephemeral=False):
        """
        Defers the response, showing a loading state.

        :param ephemeral: Should the response be ephemeral
        """
        if self.deferred or self.responded:
            raise Exception("You have already responded to this interaction!")

        payload = {"type": 5}
        if ephemeral:
            payload["data"] = {"flags": 64}

        await self._client.http.post_initial_response(payload, self.interaction_id, self._token)
        self.ephemeral = ephemeral
        self.deferred = True

    async def send(
        self,
        content: str = "",
        embeds: List[Embed] = None,
        tts: bool = False,
        allowed_mentions: dict = None,
        ephemeral: bool = False,
        components: List[Union[Dict, ActionRow]] = None,
    ):
        message = {
            "content": content,
            "tts": tts,
            "embeds": [e.to_dict() for e in embeds] if embeds else [],
            "allowed_mentions": {},
            "components": process_components(components) if components else [],
        }

        if ephemeral or (self.ephemeral and self.deferred):
            message["flags"] = 64

        if not self.responded:
            if self.deferred:
                await self._client.http.edit(message, self._client.user.id, self._token)
                self.deferred = False
            else:
                payload = {"type": 4, "data": message}
                await self._client.http.post_initial_response(payload, self.interaction_id, self._token)
            self.responded = True
        else:
            await self._client.http.post_followup(message, self._client.user.id, self._token)


@attr.s
class ComponentContext(InteractionContext):
    custom_id: str = attr.ib(default="")
    component_type: int = attr.ib(default=0)

    values: List = attr.ib(factory=list)

    defer_edit_origin: bool = attr.ib(default=False)

    @classmethod
    def from_dict(cls, data: Dict, client):
        """Create a context object from a dictionary"""
        return cls(
            client=client,
            token=data["token"],
            interaction_id=data["id"],
            custom_id=data["data"]["custom_id"],
            component_type=data["data"]["component_type"],
            data=data,
        )

    async def defer(self, ephemeral=False, edit_origin: bool = False):
        """
        Defers the response, showing a loading state.

        :param ephemeral: Should the response be ephemeral
        :param edit_origin: Whether we intend to edit the original message
        """
        if self.deferred or self.responded:
            raise Exception("You have already responded to this interaction!")

        payload = {"type": 6 if edit_origin else 5}

        if ephemeral:
            if edit_origin:
                raise ValueError("`edit_origin` and `ephemeral` are mutually exclusive")
            payload["data"] = {"flags": 64}

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
    ):
        """Edits the original message of the component."""

        message: Dict[str, Any] = {}

        if content:
            message["content"] = str(content)

        if components:
            message["components"] = process_components(components)
        if embeds:
            message["embeds"] = embeds

        if self.deferred:
            await self._client.http.edit(message, self._client.user.id, self._token)
            self.deferred = False
            self.defer_edit_origin = False
        else:
            payload = {"type": 7, "data": message}
            await self._client.http.post_initial_response(payload, self.interaction_id, self._token)
