from typing import Any
from typing import Dict
from typing import List

import attr

from dis_snek.models.discord_objects.channel import BaseChannel
from dis_snek.models.discord_objects.components import BaseComponent
from dis_snek.models.discord_objects.embed import Embed
from dis_snek.models.discord_objects.guild import Guild
from dis_snek.models.discord_objects.message import Message
from dis_snek.models.discord_objects.user import User


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

    deferred: bool = attr.ib(default=False)
    responded: bool = attr.ib(default=False)
    ephemeral: bool = attr.ib(default=False)

    data: Dict = attr.ib(factory=dict)

    values: List = attr.ib(factory=list)

    @classmethod
    def from_dict(cls, data: Dict, client):
        """Create a context object from a dictionary"""
        cls._client = client
        cls._token = data["token"]
        cls.interaction_id = data["id"]
        cls.data = data

        return cls()

    async def defer(self, ephemeral=False):
        """
        Defers the response, showing a loading state.

        :param hidden: Should the response be ephemeral
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
        components: List[BaseComponent] = None,
    ):
        message = {
            "content": content,
            "tts": tts,
            "embeds": [e.to_dict() for e in embeds] if embeds else [],
            "allowed_mentions": {},
            "components": components or [],
        }

        if ephemeral or self.ephemeral:
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
