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

import attrs

import naff.models
from naff.api.events.base import GuildEvent, BaseEvent
from naff.client.const import Absent
from naff.client.utils.attr_utils import docs

__all__ = (
    "ApplicationCommandPermissionsUpdate",
    "AutoModCreated",
    "AutoModDeleted",
    "AutoModExec",
    "AutoModUpdated",
    "BanCreate",
    "BanRemove",
    "BaseVoiceEvent",
    "ChannelCreate",
    "ChannelDelete",
    "ChannelPinsUpdate",
    "ChannelUpdate",
    "GuildEmojisUpdate",
    "GuildJoin",
    "GuildLeft",
    "GuildMembersChunk",
    "GuildStickersUpdate",
    "GuildAvailable",
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
    "NewThreadCreate",
    "PresenceUpdate",
    "RoleCreate",
    "RoleDelete",
    "RoleUpdate",
    "StageInstanceCreate",
    "StageInstanceDelete",
    "StageInstanceUpdate",
    "ThreadCreate",
    "ThreadDelete",
    "ThreadListSync",
    "ThreadMembersUpdate",
    "ThreadMemberUpdate",
    "ThreadUpdate",
    "TypingStart",
    "VoiceStateUpdate",
    "VoiceUserDeafen",
    "VoiceUserJoin",
    "VoiceUserLeave",
    "VoiceUserMove",
    "VoiceUserMute",
    "WebhooksUpdate",
)


if TYPE_CHECKING:
    from naff.models.discord.guild import Guild, GuildIntegration
    from naff.models.discord.channel import BaseChannel, TYPE_THREAD_CHANNEL, VoiceChannel
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
    from naff.models.discord.auto_mod import AutoModerationAction, AutoModRule
    from naff.models.discord.reaction import Reaction
    from naff.models.discord.app_perms import ApplicationCommandPermission


@attrs.define(eq=False, order=False, hash=False, kw_only=False)
class AutoModExec(BaseEvent):
    """Dispatched when an auto modation action is executed"""

    execution: "AutoModerationAction" = attrs.field(repr=False, metadata=docs("The executed auto mod action"))
    channel: "BaseChannel" = attrs.field(repr=False, metadata=docs("The channel the action was executed in"))
    guild: "Guild" = attrs.field(repr=False, metadata=docs("The guild the action was executed in"))


@attrs.define(eq=False, order=False, hash=False, kw_only=False)
class AutoModCreated(BaseEvent):
    guild: "Guild" = attrs.field(repr=False, metadata=docs("The guild the rule was modified in"))
    rule: "AutoModRule" = attrs.field(repr=False, metadata=docs("The rule that was modified"))


@attrs.define(eq=False, order=False, hash=False, kw_only=False)
class AutoModUpdated(AutoModCreated):
    """Dispatched when an auto mod rule is modified"""

    ...


@attrs.define(eq=False, order=False, hash=False, kw_only=False)
class AutoModDeleted(AutoModCreated):
    """Dispatched when an auto mod rule is deleted"""

    ...


@attrs.define(eq=False, order=False, hash=False, kw_only=False)
class ApplicationCommandPermissionsUpdate(BaseEvent):
    guild_id: "Snowflake_Type" = attrs.field(
        repr=False, metadata=docs("The guild the command permissions were updated in")
    )
    application_id: "Snowflake_Type" = attrs.field(
        repr=False, metadata=docs("The application the command permissions were updated for")
    )
    permissions: List["ApplicationCommandPermission"] = attrs.field(
        repr=False, factory=list, metadata=docs("The updated permissions")
    )


@attrs.define(eq=False, order=False, hash=False, kw_only=False)
class ChannelCreate(BaseEvent):
    """Dispatched when a channel is created."""

    channel: "BaseChannel" = attrs.field(repr=False, metadata=docs("The channel this event is dispatched from"))


@attrs.define(eq=False, order=False, hash=False, kw_only=False)
class ChannelUpdate(BaseEvent):
    """Dispatched when a channel is updated."""

    before: "BaseChannel" = attrs.field(
        repr=False,
    )
    """Channel before this event. MISSING if it was not cached before"""
    after: "BaseChannel" = attrs.field(
        repr=False,
    )
    """Channel after this event"""


@attrs.define(eq=False, order=False, hash=False, kw_only=False)
class ChannelDelete(ChannelCreate):
    """Dispatched when a channel is deleted."""


@attrs.define(eq=False, order=False, hash=False, kw_only=False)
class ChannelPinsUpdate(ChannelCreate):
    """Dispatched when a channel's pins are updated."""

    last_pin_timestamp: "Timestamp" = attrs.field(
        repr=False,
    )
    """The time at which the most recent pinned message was pinned"""


@attrs.define(eq=False, order=False, hash=False, kw_only=False)
class ThreadCreate(BaseEvent):
    """Dispatched when a thread is created, or a thread is new to the client"""

    thread: "TYPE_THREAD_CHANNEL" = attrs.field(repr=False, metadata=docs("The thread this event is dispatched from"))


@attrs.define(eq=False, order=False, hash=False, kw_only=False)
class NewThreadCreate(ThreadCreate):
    """Dispatched when a thread is newly created."""


@attrs.define(eq=False, order=False, hash=False, kw_only=False)
class ThreadUpdate(ThreadCreate):
    """Dispatched when a thread is updated."""


@attrs.define(eq=False, order=False, hash=False, kw_only=False)
class ThreadDelete(ThreadCreate):
    """Dispatched when a thread is deleted."""


@attrs.define(eq=False, order=False, hash=False, kw_only=False)
class ThreadListSync(BaseEvent):
    """Dispatched when gaining access to a channel, contains all active threads in that channel."""

    channel_ids: Sequence["Snowflake_Type"] = attrs.field(
        repr=False,
    )
    """The parent channel ids whose threads are being synced. If omitted, then threads were synced for the entire guild. This array may contain channel_ids that have no active threads as well, so you know to clear that data."""
    threads: List["BaseChannel"] = attrs.field(
        repr=False,
    )
    """all active threads in the given channels that the current user can access"""
    members: List["Member"] = attrs.field(
        repr=False,
    )
    """all thread member objects from the synced threads for the current user, indicating which threads the current user has been added to"""


# todo implementation missing
@attrs.define(eq=False, order=False, hash=False, kw_only=False)
class ThreadMemberUpdate(ThreadCreate):
    """
    Dispatched when the thread member object for the current user is updated.

    ??? info "Note from Discord"     This event is documented for
    completeness, but unlikely to be used by most bots. For bots, this
    event largely is just a signal that you are a member of the thread

    """

    member: "Member" = attrs.field(
        repr=False,
    )
    """The member who was added"""


@attrs.define(eq=False, order=False, hash=False, kw_only=False)
class ThreadMembersUpdate(BaseEvent):
    """Dispatched when anyone is added or removed from a thread."""

    id: "Snowflake_Type" = attrs.field(
        repr=False,
    )
    """The ID of the thread"""
    member_count: int = attrs.field(repr=False, default=50)
    """the approximate number of members in the thread, capped at 50"""
    added_members: List["Member"] = attrs.field(repr=False, factory=list)
    """Users added to the thread"""
    removed_member_ids: List["Snowflake_Type"] = attrs.field(repr=False, factory=list)
    """Users removed from the thread"""


@attrs.define(eq=False, order=False, hash=False, kw_only=False)
class GuildJoin(GuildEvent):
    """
    Dispatched when a guild is joined, created, or becomes available.

    !!! note
        This is called multiple times during startup, check the bot is ready before responding to this.

    """


@attrs.define(eq=False, order=False, hash=False, kw_only=False)
class GuildUpdate(BaseEvent):
    """Dispatched when a guild is updated."""

    before: "Guild" = attrs.field(
        repr=False,
    )
    """Guild before this event"""
    after: "Guild" = attrs.field(
        repr=False,
    )
    """Guild after this event"""


@attrs.define(eq=False, order=False, hash=False, kw_only=False)
class GuildLeft(BaseEvent):
    """Dispatched when a guild is left."""

    guild: "Guild" = attrs.field(repr=True)
    """The guild this event is dispatched from"""


@attrs.define(eq=False, order=False, hash=False, kw_only=False)
class GuildAvailable(GuildEvent):
    """Dispatched when a guild becomes available."""


@attrs.define(eq=False, order=False, hash=False, kw_only=False)
class GuildUnavailable(GuildEvent):
    """Dispatched when a guild is not available."""


@attrs.define(eq=False, order=False, hash=False, kw_only=False)
class BanCreate(GuildEvent):
    """Dispatched when someone was banned from a guild."""

    user: "BaseUser" = attrs.field(repr=False, metadata=docs("The user"))


@attrs.define(eq=False, order=False, hash=False, kw_only=False)
class BanRemove(BanCreate):
    """Dispatched when a users ban is removed."""


@attrs.define(eq=False, order=False, hash=False, kw_only=False)
class GuildEmojisUpdate(GuildEvent):
    """Dispatched when a guild's emojis are updated."""

    before: List["CustomEmoji"] = attrs.field(repr=False, factory=list)
    """List of emoji before this event. Only includes emojis that were cached. To enable the emoji cache (and this field), start your bot with `Client(enable_emoji_cache=True)`"""
    after: List["CustomEmoji"] = attrs.field(repr=False, factory=list)
    """List of emoji after this event"""


@attrs.define(eq=False, order=False, hash=False, kw_only=False)
class GuildStickersUpdate(GuildEvent):
    """Dispatched when a guild's stickers are updated."""

    stickers: List["Sticker"] = attrs.field(repr=False, factory=list)
    """List of stickers from after this event"""


@attrs.define(eq=False, order=False, hash=False, kw_only=False)
class MemberAdd(GuildEvent):
    """Dispatched when a member is added to a guild."""

    member: "Member" = attrs.field(repr=False, metadata=docs("The member who was added"))


@attrs.define(eq=False, order=False, hash=False, kw_only=False)
class MemberRemove(MemberAdd):
    """Dispatched when a member is removed from a guild."""

    member: Union["Member", "User"] = attrs.field(
        repr=False, metadata=docs("The member who was added, can be user if the member is not cached")
    )


@attrs.define(eq=False, order=False, hash=False, kw_only=False)
class MemberUpdate(GuildEvent):
    """Dispatched when a member is updated."""

    before: "Member" = attrs.field(
        repr=False,
    )
    """The state of the member before this event"""
    after: "Member" = attrs.field(
        repr=False,
    )
    """The state of the member after this event"""


@attrs.define(eq=False, order=False, hash=False, kw_only=False)
class RoleCreate(GuildEvent):
    """Dispatched when a role is created."""

    role: "Role" = attrs.field(
        repr=False,
    )
    """The created role"""


@attrs.define(eq=False, order=False, hash=False, kw_only=False)
class RoleUpdate(GuildEvent):
    """Dispatched when a role is updated."""

    before: Absent["Role"] = attrs.field(
        repr=False,
    )
    """The role before this event"""
    after: "Role" = attrs.field(
        repr=False,
    )
    """The role after this event"""


@attrs.define(eq=False, order=False, hash=False, kw_only=False)
class RoleDelete(GuildEvent):
    """Dispatched when a guild role is deleted."""

    id: "Snowflake_Type" = attrs.field(
        repr=False,
    )
    """The ID of the deleted role"""
    role: Absent["Role"] = attrs.field(
        repr=False,
    )
    """The deleted role"""


@attrs.define(eq=False, order=False, hash=False, kw_only=False)
class GuildMembersChunk(GuildEvent):
    """
    Sent in response to Guild Request Members.

    You can use the `chunk_index` and `chunk_count` to calculate how
    many chunks are left for your request.

    """

    chunk_index: int = attrs.field(
        repr=False,
    )
    """The chunk index in the expected chunks for this response (0 <= chunk_index < chunk_count)"""
    chunk_count: int = attrs.field(
        repr=False,
    )
    """the total number of expected chunks for this response"""
    presences: List = attrs.field(
        repr=False,
    )
    """if passing true to `REQUEST_GUILD_MEMBERS`, presences of the returned members will be here"""
    nonce: str = attrs.field(
        repr=False,
    )
    """The nonce used in the request, if any"""
    members: List["Member"] = attrs.field(repr=False, factory=list)
    """A list of members"""


@attrs.define(eq=False, order=False, hash=False, kw_only=False)
class IntegrationCreate(BaseEvent):
    """Dispatched when a guild integration is created."""

    integration: "GuildIntegration" = attrs.field(
        repr=False,
    )


@attrs.define(eq=False, order=False, hash=False, kw_only=False)
class IntegrationUpdate(IntegrationCreate):
    """Dispatched when a guild integration is updated."""


@attrs.define(eq=False, order=False, hash=False, kw_only=False)
class IntegrationDelete(GuildEvent):
    """Dispatched when a guild integration is deleted."""

    id: "Snowflake_Type" = attrs.field(
        repr=False,
    )
    """The ID of the integration"""
    application_id: "Snowflake_Type" = attrs.field(repr=False, default=None)
    """The ID of the bot/application for this integration"""


@attrs.define(eq=False, order=False, hash=False, kw_only=False)
class InviteCreate(BaseEvent):
    """Dispatched when a guild invite is created."""

    invite: naff.models.Invite = attrs.field(
        repr=False,
    )


@attrs.define(eq=False, order=False, hash=False, kw_only=False)
class InviteDelete(InviteCreate):
    """Dispatched when an invite is deleted."""


@attrs.define(eq=False, order=False, hash=False, kw_only=False)
class MessageCreate(BaseEvent):
    """Dispatched when a message is created."""

    message: "Message" = attrs.field(
        repr=False,
    )


@attrs.define(eq=False, order=False, hash=False, kw_only=False)
class MessageUpdate(BaseEvent):
    """Dispatched when a message is edited."""

    before: "Message" = attrs.field(
        repr=False,
    )
    """The message before this event was created"""
    after: "Message" = attrs.field(
        repr=False,
    )
    """The message after this event was created"""


@attrs.define(eq=False, order=False, hash=False, kw_only=False)
class MessageDelete(BaseEvent):
    """Dispatched when a message is deleted."""

    message: "Message" = attrs.field(
        repr=False,
    )


@attrs.define(eq=False, order=False, hash=False, kw_only=False)
class MessageDeleteBulk(GuildEvent):
    """Dispatched when multiple messages are deleted at once."""

    channel_id: "Snowflake_Type" = attrs.field(
        repr=False,
    )
    """The ID of the channel these were deleted in"""
    ids: List["Snowflake_Type"] = attrs.field(repr=False, factory=list)
    """A list of message snowflakes"""


@attrs.define(eq=False, order=False, hash=False, kw_only=False)
class MessageReactionAdd(BaseEvent):
    """Dispatched when a reaction is added to a message."""

    message: "Message" = attrs.field(repr=False, metadata=docs("The message that was reacted to"))
    emoji: "PartialEmoji" = attrs.field(repr=False, metadata=docs("The emoji that was added to the message"))
    author: Union["Member", "User"] = attrs.field(repr=False, metadata=docs("The user who added the reaction"))
    # reaction can be None when the message is not in the cache, and it was the last reaction, and it was deleted in the event
    reaction: Optional["Reaction"] = attrs.field(
        repr=False, default=None, metadata=docs("The reaction object corresponding to the emoji")
    )

    @property
    def reaction_count(self) -> int:
        """Times the emoji in the event has been used to react"""
        if self.reaction is None:
            return 0
        return self.reaction.count


@attrs.define(eq=False, order=False, hash=False, kw_only=False)
class MessageReactionRemove(MessageReactionAdd):
    """Dispatched when a reaction is removed."""


@attrs.define(eq=False, order=False, hash=False, kw_only=False)
class MessageReactionRemoveAll(GuildEvent):
    """Dispatched when all reactions are removed from a message."""

    message: "Message" = attrs.field(
        repr=False,
    )
    """The message that was reacted to"""


@attrs.define(eq=False, order=False, hash=False, kw_only=False)
class PresenceUpdate(BaseEvent):
    """A user's presence has changed."""

    user: "User" = attrs.field(
        repr=False,
    )
    """The user in question"""
    status: str = attrs.field(
        repr=False,
    )
    """'Either `idle`, `dnd`, `online`, or `offline`'"""
    activities: List["Activity"] = attrs.field(
        repr=False,
    )
    """The users current activities"""
    client_status: dict = attrs.field(
        repr=False,
    )
    """What platform the user is reported as being on"""
    guild_id: "Snowflake_Type" = attrs.field(
        repr=False,
    )
    """The guild this presence update was dispatched from"""


@attrs.define(eq=False, order=False, hash=False, kw_only=False)
class StageInstanceCreate(BaseEvent):
    """Dispatched when a stage instance is created."""

    stage_instance: "StageInstance" = attrs.field(repr=False, metadata=docs("The stage instance"))


@attrs.define(eq=False, order=False, hash=False, kw_only=False)
class StageInstanceDelete(StageInstanceCreate):
    """Dispatched when a stage instance is deleted."""


@attrs.define(eq=False, order=False, hash=False, kw_only=False)
class StageInstanceUpdate(StageInstanceCreate):
    """Dispatched when a stage instance is updated."""


@attrs.define(eq=False, order=False, hash=False, kw_only=False)
class TypingStart(BaseEvent):
    """Dispatched when a user starts typing."""

    author: Union["User", "Member"] = attrs.field(
        repr=False,
    )
    """The user who started typing"""
    channel: "BaseChannel" = attrs.field(
        repr=False,
    )
    """The channel typing is in"""
    guild: "Guild" = attrs.field(
        repr=False,
    )
    """The ID of the guild this typing is in"""
    timestamp: "Timestamp" = attrs.field(
        repr=False,
    )
    """unix time (in seconds) of when the user started typing"""


@attrs.define(eq=False, order=False, hash=False, kw_only=False)
class WebhooksUpdate(GuildEvent):
    """Dispatched when a guild channel webhook is created, updated, or deleted."""

    # Discord doesnt sent the webhook object for this event, for some reason
    channel_id: "Snowflake_Type" = attrs.field(
        repr=False,
    )
    """The ID of the webhook was updated"""


@attrs.define(eq=False, order=False, hash=False, kw_only=False)
class InteractionCreate(BaseEvent):
    """Dispatched when a user uses an Application Command."""

    interaction: dict = attrs.field(
        repr=False,
    )


@attrs.define(eq=False, order=False, hash=False, kw_only=False)
class VoiceStateUpdate(BaseEvent):
    """Dispatched when a user's voice state changes."""

    before: Optional["VoiceState"] = attrs.field(
        repr=False,
    )
    """The voice state before this event was created or None if the user was not in a voice channel"""
    after: Optional["VoiceState"] = attrs.field(
        repr=False,
    )
    """The voice state after this event was created or None if the user is no longer in a voice channel"""


@attrs.define(eq=False, order=False, hash=False, kw_only=False)
class BaseVoiceEvent(BaseEvent):
    state: "VoiceState" = attrs.field(
        repr=False,
    )
    """The current voice state of the user"""


@attrs.define(eq=False, order=False, hash=False, kw_only=False)
class VoiceUserMove(BaseVoiceEvent):
    """Dispatched when a user moves voice channels."""

    author: Union["User", "Member"] = attrs.field(
        repr=False,
    )

    previous_channel: "VoiceChannel" = attrs.field(
        repr=False,
    )
    """The previous voice channel the user was in"""
    new_channel: "VoiceChannel" = attrs.field(
        repr=False,
    )
    """The new voice channel the user is in"""


@attrs.define(eq=False, order=False, hash=False, kw_only=False)
class VoiceUserMute(BaseVoiceEvent):
    """Dispatched when a user is muted or unmuted."""

    author: Union["User", "Member"] = attrs.field(
        repr=False,
    )
    """The user who was muted or unmuted"""
    channel: "VoiceChannel" = attrs.field(
        repr=False,
    )
    """The voice channel the user was muted or unmuted in"""
    mute: bool = attrs.field(
        repr=False,
    )
    """The new mute state of the user"""


@attrs.define(eq=False, order=False, hash=False, kw_only=False)
class VoiceUserDeafen(BaseVoiceEvent):
    """Dispatched when a user is deafened or undeafened."""

    author: Union["User", "Member"] = attrs.field(
        repr=False,
    )
    """The user who was deafened or undeafened"""
    channel: "VoiceChannel" = attrs.field(
        repr=False,
    )
    """The voice channel the user was deafened or undeafened in"""
    deaf: bool = attrs.field(
        repr=False,
    )
    """The new deaf state of the user"""


@attrs.define(eq=False, order=False, hash=False, kw_only=False)
class VoiceUserJoin(BaseVoiceEvent):
    """Dispatched when a user joins a voice channel."""

    author: Union["User", "Member"] = attrs.field(
        repr=False,
    )
    """The user who joined the voice channel"""
    channel: "VoiceChannel" = attrs.field(
        repr=False,
    )
    """The voice channel the user joined"""


@attrs.define(eq=False, order=False, hash=False, kw_only=False)
class VoiceUserLeave(BaseVoiceEvent):
    """Dispatched when a user leaves a voice channel."""

    author: Union["User", "Member"] = attrs.field(
        repr=False,
    )
    """The user who left the voice channel"""
    channel: "VoiceChannel" = attrs.field(
        repr=False,
    )
    """The voice channel the user left"""
