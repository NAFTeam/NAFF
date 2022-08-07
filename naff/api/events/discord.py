"""
These are events dispatched by Discord. This is intended as a reference so you know what data to expect for each event.

??? Hint "Example Usage:"
    The event classes outlined here are in `CamelCase` to comply with Class naming convention, however the event names
    are actually in `lower_case_with_underscores` so your listeners should be named as following:

    ```python
    @listen()
    def on_ready():
        # ready events pass no data, so dont have params
        print("Im ready!")

    @listen()
    def on_guild_join(event):
        # guild_create events pass a guild object, expect a single param
        print(f"{event.guild.name} created")
    ```
!!! warning
    While all of these events are documented, not all of them are used, currently.

"""

from typing import TYPE_CHECKING, List, Sequence, Union, Optional

import naff.models
from naff.client.const import MISSING, Absent
from naff.client.utils.attr_utils import define, field, docs
from .internal import BaseEvent, GuildEvent

__all__ = (
    "BanCreate",
    "BanRemove",
    "AutoModExec",
    "AutoModCreated",
    "AutoModUpdated",
    "AutoModDeleted",
    "ChannelCreate",
    "ChannelDelete",
    "ChannelPinsUpdate",
    "ChannelUpdate",
    "GuildEmojisUpdate",
    "GuildJoin",
    "GuildLeft",
    "GuildMembersChunk",
    "GuildStickersUpdate",
    "GuildUnavailable",
    "GuildUpdate",
    "IntegrationCreate",
    "IntegrationDelete",
    "IntegrationUpdate",
    "InteractionCreate",
    "InviteCreate",
    "InviteDelete",
    "MemberAdd",
    "MemberRemove",
    "MemberUpdate",
    "MessageCreate",
    "MessageDelete",
    "MessageDeleteBulk",
    "MessageReactionAdd",
    "MessageReactionRemove",
    "MessageReactionRemoveAll",
    "MessageUpdate",
    "ModalResponse",
    "PresenceUpdate",
    "RawGatewayEvent",
    "RoleCreate",
    "RoleDelete",
    "RoleUpdate",
    "StageInstanceCreate",
    "StageInstanceDelete",
    "StageInstanceUpdate",
    "ThreadCreate",
    "ThreadDelete",
    "ThreadListSync",
    "ThreadMemberUpdate",
    "ThreadMembersUpdate",
    "ThreadUpdate",
    "TypingStart",
    "VoiceStateUpdate",
    "WebhooksUpdate",
)


if TYPE_CHECKING:
    from naff.models.discord.guild import Guild, GuildIntegration
    from naff.models.discord.channel import BaseChannel, TYPE_THREAD_CHANNEL
    from naff.models.discord.message import Message
    from naff.models.discord.timestamp import Timestamp
    from naff.models.discord.user import Member, User, BaseUser
    from naff.models.discord.snowflake import Snowflake_Type
    from naff.models.discord.activity import Activity
    from naff.models.discord.emoji import CustomEmoji, PartialEmoji
    from naff.models.discord.role import Role
    from naff.models.discord.sticker import Sticker
    from naff.models.discord.voice_state import VoiceState
    from naff.models.discord.stage_instance import StageInstance
    from naff.models.naff.context import ModalContext
    from naff.models.discord.auto_mod import AutoModerationAction, AutoModRule
    from naff.models.discord.reaction import Reaction


@define(kw_only=False)
class RawGatewayEvent(BaseEvent):
    """
    An event dispatched from the gateway.

    Holds the raw dict that the gateway dispatches

    """

    data: dict = field(factory=dict)
    """Raw Data from the gateway"""


@define(kw_only=False)
class AutoModExec(BaseEvent):
    """Dispatched when an auto modation action is executed"""

    execution: "AutoModerationAction" = field(metadata=docs("The executed auto mod action"))
    channel: "BaseChannel" = field(metadata=docs("The channel the action was executed in"))
    guild: "Guild" = field(metadata=docs("The guild the action was executed in"))


@define(kw_only=False)
class AutoModCreated(BaseEvent):
    guild: "Guild" = field(metadata=docs("The guild the rule was modified in"))
    rule: "AutoModRule" = field(metadata=docs("The rule that was modified"))


@define(kw_only=False)
class AutoModUpdated(AutoModCreated):
    """Dispatched when an auto mod rule is modified"""

    ...


@define(kw_only=False)
class AutoModDeleted(AutoModCreated):
    """Dispatched when an auto mod rule is deleted"""

    ...


@define(kw_only=False)
class ChannelCreate(BaseEvent):
    """Dispatched when a channel is created."""

    channel: "BaseChannel" = field(metadata=docs("The channel this event is dispatched from"))


@define(kw_only=False)
class ChannelUpdate(BaseEvent):
    """Dispatched when a channel is updated."""

    before: "BaseChannel" = field()
    """Channel before this event. MISSING if it was not cached before"""
    after: "BaseChannel" = field()
    """Channel after this event"""


@define(kw_only=False)
class ChannelDelete(ChannelCreate):
    """Dispatched when a channel is deleted."""


@define(kw_only=False)
class ChannelPinsUpdate(ChannelCreate):
    """Dispatched when a channel's pins are updated."""

    last_pin_timestamp: "Timestamp" = field()
    """The time at which the most recent pinned message was pinned"""


@define(kw_only=False)
class ThreadCreate(BaseEvent):
    """Dispatched when a thread is created."""

    thread: "TYPE_THREAD_CHANNEL" = field(metadata=docs("The thread this event is dispatched from"))


@define(kw_only=False)
class ThreadUpdate(ThreadCreate):
    """Dispatched when a thread is updated."""


@define(kw_only=False)
class ThreadDelete(ThreadCreate):
    """Dispatched when a thread is deleted."""


@define(kw_only=False)
class ThreadListSync(BaseEvent):
    """Dispatched when gaining access to a channel, contains all active threads in that channel."""

    channel_ids: Sequence["Snowflake_Type"] = field()
    """The parent channel ids whose threads are being synced. If omitted, then threads were synced for the entire guild. This array may contain channel_ids that have no active threads as well, so you know to clear that data."""
    threads: List["BaseChannel"] = field()
    """all active threads in the given channels that the current user can access"""
    members: List["Member"] = field()
    """all thread member objects from the synced threads for the current user, indicating which threads the current user has been added to"""


# todo implementation missing
@define(kw_only=False)
class ThreadMemberUpdate(ThreadCreate):
    """
    Dispatched when the thread member object for the current user is updated.

    ??? info "Note from Discord"     This event is documented for
    completeness, but unlikely to be used by most bots. For bots, this
    event largely is just a signal that you are a member of the thread

    """

    member: "Member" = field()
    """The member who was added"""


@define(kw_only=False)
class ThreadMembersUpdate(BaseEvent):
    """Dispatched when anyone is added or removed from a thread."""

    id: "Snowflake_Type" = field()
    """The ID of the thread"""
    member_count: int = field(default=50)
    """the approximate number of members in the thread, capped at 50"""
    added_members: List["Member"] = field(factory=list)
    """Users added to the thread"""
    removed_member_ids: List["Snowflake_Type"] = field(factory=list)
    """Users removed from the thread"""


@define(kw_only=False)
class GuildJoin(BaseEvent):
    """
    Dispatched when a guild is joined, created, or becomes available.

    !!! note
        This is called multiple times during startup, check the bot is ready before responding to this.

    """

    guild: "Guild" = field()
    """The guild that was created"""


@define(kw_only=False)
class GuildUpdate(BaseEvent):
    """Dispatched when a guild is updated."""

    before: "Guild" = field()
    """Guild before this event"""
    after: "Guild" = field()
    """Guild after this event"""


@define(kw_only=False)
class GuildLeft(BaseEvent, GuildEvent):
    """Dispatched when a guild is left."""

    guild: Optional["Guild"] = field(default=MISSING)
    """The guild, if it was cached"""


@define(kw_only=False)
class GuildUnavailable(BaseEvent, GuildEvent):
    """Dispatched when a guild is not available."""

    guild: Optional["Guild"] = field(default=MISSING)
    """The guild, if it was cached"""


@define(kw_only=False)
class BanCreate(BaseEvent, GuildEvent):
    """Dispatched when someone was banned from a guild."""

    user: "BaseUser" = field(metadata=docs("The user"))


@define(kw_only=False)
class BanRemove(BanCreate):
    """Dispatched when a users ban is removed."""


@define(kw_only=False)
class GuildEmojisUpdate(BaseEvent, GuildEvent):
    """Dispatched when a guild's emojis are updated."""

    before: List["CustomEmoji"] = field(factory=list)
    """List of emoji before this event. Only includes emojis that were cached. To enable the emoji cache (and this field), start your bot with `Client(enable_emoji_cache=True)`"""
    after: List["CustomEmoji"] = field(factory=list)
    """List of emoji after this event"""


@define(kw_only=False)
class GuildStickersUpdate(BaseEvent, GuildEvent):
    """Dispatched when a guild's stickers are updated."""

    stickers: List["Sticker"] = field(factory=list)
    """List of stickers from after this event"""


@define(kw_only=False)
class MemberAdd(BaseEvent, GuildEvent):
    """Dispatched when a member is added to a guild."""

    member: "Member" = field(metadata=docs("The member who was added"))


@define(kw_only=False)
class MemberRemove(MemberAdd):
    """Dispatched when a member is removed from a guild."""

    member: Union["Member", "User"] = field(
        metadata=docs("The member who was added, can be user if the member is not cached")
    )


@define(kw_only=False)
class MemberUpdate(BaseEvent, GuildEvent):
    """Dispatched when a member is updated."""

    before: "Member" = field()
    """The state of the member before this event"""
    after: "Member" = field()
    """The state of the member after this event"""


@define(kw_only=False)
class RoleCreate(BaseEvent, GuildEvent):
    """Dispatched when a role is created."""

    role: "Role" = field()
    """The created role"""


@define(kw_only=False)
class RoleUpdate(BaseEvent, GuildEvent):
    """Dispatched when a role is updated."""

    before: Absent["Role"] = field()
    """The role before this event"""
    after: "Role" = field()
    """The role after this event"""


@define(kw_only=False)
class RoleDelete(BaseEvent, GuildEvent):
    """Dispatched when a guild role is deleted."""

    id: "Snowflake_Type" = field()
    """The ID of the deleted role"""
    role: Absent["Role"] = field()
    """The deleted role"""


@define(kw_only=False)
class GuildMembersChunk(BaseEvent, GuildEvent):
    """
    Sent in response to Guild Request Members.

    You can use the `chunk_index` and `chunk_count` to calculate how
    many chunks are left for your request.

    """

    chunk_index: int = field()
    """The chunk index in the expected chunks for this response (0 <= chunk_index < chunk_count)"""
    chunk_count: int = field()
    """the total number of expected chunks for this response"""
    presences: List = field()
    """if passing true to `REQUEST_GUILD_MEMBERS`, presences of the returned members will be here"""
    nonce: str = field()
    """The nonce used in the request, if any"""
    members: List["Member"] = field(factory=list)
    """A list of members"""


@define(kw_only=False)
class IntegrationCreate(BaseEvent):
    """Dispatched when a guild integration is created."""

    integration: "GuildIntegration" = field()


@define(kw_only=False)
class IntegrationUpdate(IntegrationCreate):
    """Dispatched when a guild integration is updated."""


@define(kw_only=False)
class IntegrationDelete(BaseEvent, GuildEvent):
    """Dispatched when a guild integration is deleted."""

    id: "Snowflake_Type" = field()
    """The ID of the integration"""
    application_id: "Snowflake_Type" = field(default=None)
    """The ID of the bot/application for this integration"""


@define(kw_only=False)
class InviteCreate(BaseEvent):
    """Dispatched when a guild invite is created."""

    invite: naff.models.Invite = field()


@define(kw_only=False)
class InviteDelete(InviteCreate):
    """Dispatched when an invite is deleted."""


@define(kw_only=False)
class MessageCreate(BaseEvent):
    """Dispatched when a message is created."""

    message: "Message" = field()


@define(kw_only=False)
class MessageUpdate(BaseEvent):
    """Dispatched when a message is edited."""

    before: "Message" = field()
    """The message before this event was created"""
    after: "Message" = field()
    """The message after this event was created"""


@define(kw_only=False)
class MessageDelete(BaseEvent):
    """Dispatched when a message is deleted."""

    message: "Message" = field()


@define(kw_only=False)
class MessageDeleteBulk(BaseEvent, GuildEvent):
    """Dispatched when multiple messages are deleted at once."""

    channel_id: "Snowflake_Type" = field()
    """The ID of the channel these were deleted in"""
    ids: List["Snowflake_Type"] = field(factory=list)
    """A list of message snowflakes"""


@define(kw_only=False)
class MessageReactionAdd(BaseEvent):
    """Dispatched when a reaction is added to a message."""

    message: "Message" = field(metadata=docs("The message that was reacted to"))
    emoji: "PartialEmoji" = field(metadata=docs("The emoji that was added to the message"))
    author: Union["Member", "User"] = field(metadata=docs("The user who added the reaction"))
    # reaction can be None when the message is not in the cache, and it was the last reaction, and it was deleted in the event
    reaction: Optional["Reaction"] = field(
        default=None, metadata=docs("The reaction object corresponding to the emoji")
    )

    @property
    def reaction_count(self) -> int:
        """Times the emoji in the event has been used to react"""
        if self.reaction is None:
            return 0
        return self.reaction.count


@define(kw_only=False)
class MessageReactionRemove(MessageReactionAdd):
    """Dispatched when a reaction is removed."""


@define(kw_only=False)
class MessageReactionRemoveAll(BaseEvent, GuildEvent):
    """Dispatched when all reactions are removed from a message."""

    message: "Message" = field()
    """The message that was reacted to"""


@define(kw_only=False)
class PresenceUpdate(BaseEvent):
    """A user's presence has changed."""

    user: "User" = field()
    """The user in question"""
    status: str = field()
    """'Either `idle`, `dnd`, `online`, or `offline`'"""
    activities: List["Activity"] = field()
    """The users current activities"""
    client_status: dict = field()
    """What platform the user is reported as being on"""
    guild_id: "Snowflake_Type" = field()
    """The guild this presence update was dispatched from"""


@define(kw_only=False)
class StageInstanceCreate(BaseEvent):
    """Dispatched when a stage instance is created."""

    stage_instance: "StageInstance" = field(metadata=docs("The stage instance"))


@define(kw_only=False)
class StageInstanceDelete(StageInstanceCreate):
    """Dispatched when a stage instance is deleted."""


@define(kw_only=False)
class StageInstanceUpdate(StageInstanceCreate):
    """Dispatched when a stage instance is updated."""


@define(kw_only=False)
class TypingStart(BaseEvent):
    """Dispatched when a user starts typing."""

    author: Union["User", "Member"] = field()
    """The user who started typing"""
    channel: "BaseChannel" = field()
    """The channel typing is in"""
    guild: "Guild" = field()
    """The ID of the guild this typing is in"""
    timestamp: "Timestamp" = field()
    """unix time (in seconds) of when the user started typing"""


@define(kw_only=False)
class WebhooksUpdate(BaseEvent, GuildEvent):
    """Dispatched when a guild channel webhook is created, updated, or deleted."""

    # Discord doesnt sent the webhook object for this event, for some reason
    channel_id: "Snowflake_Type" = field()
    """The ID of the webhook was updated"""


@define(kw_only=False)
class InteractionCreate(BaseEvent):
    """Dispatched when a user uses an Application Command."""

    interaction: dict = field()


@define(kw_only=False)
class ModalResponse(BaseEvent):
    """Dispatched when a modal receives a response"""

    context: "ModalContext" = field()
    """The context data of the modal"""


@define(kw_only=False)
class VoiceStateUpdate(BaseEvent):
    """Dispatched when a user joins/leaves/moves voice channels."""

    before: Optional["VoiceState"] = field()
    """The voice state before this event was created or None if the user was not in a voice channel"""
    after: Optional["VoiceState"] = field()
    """The voice state after this event was created or None if the user is no longer in a voice channel"""
