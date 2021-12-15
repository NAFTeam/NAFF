"""
These are events dispatched by Discord. This is intended as a reference so you know what data to expect for each event

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

from typing import TYPE_CHECKING, Any, List, Union, Optional

import attr
from dis_snek.models.discord_objects.stage_instance import StageInstance

from dis_snek.models import Invite

from dis_snek.const import MISSING
from dis_snek.models.events.internal import BaseEvent, GuildEvent
from dis_snek.utils.attr_utils import docs

if TYPE_CHECKING:
    from dis_snek.models.discord_objects.guild import Guild, GuildIntegration
    from dis_snek.models.discord_objects.channel import BaseChannel, TYPE_THREAD_CHANNEL
    from dis_snek.models.discord_objects.message import Message
    from dis_snek.models.timestamp import Timestamp
    from dis_snek.models.discord_objects.user import Member, User, BaseUser
    from dis_snek.models.snowflake import Snowflake_Type
    from dis_snek.models.discord_objects.activity import Activity
    from dis_snek.models.discord_objects.emoji import Emoji
    from dis_snek.models.discord_objects.role import Role
    from dis_snek.models.discord_objects.sticker import Sticker
    from dis_snek.models.discord_objects.voice_state import VoiceState


@attr.s(slots=True)
class RawGatewayEvent(BaseEvent):
    """An event dispatched from the gateway. Holds the raw dict that the gateway dispatches"""

    data: dict = attr.ib(factory=dict)
    """Raw Data from the gateway"""


@attr.s(slots=True)
class ChannelCreate(BaseEvent):
    """Dispatched when a channel is created."""

    channel: "BaseChannel" = attr.ib(metadata=docs("The channel this event is dispatched from"))


@attr.s(slots=True)
class ChannelUpdate(ChannelCreate):
    """Dispatched when a channel is updated"""


@attr.s(slots=True)
class ChannelDelete(ChannelCreate):
    """Dispatched when a channel is deleted"""


@attr.s(slots=True)
class ChannelPinsUpdate(ChannelCreate):
    """Dispatched when a channel's pins are updated"""

    last_pin_timestamp: "Timestamp" = attr.ib()
    """The time at which the most recent pinned message was pinned"""


@attr.s(slots=True)
class ThreadCreate(BaseEvent):
    """Dispatched when a thread is created."""

    thread: "TYPE_THREAD_CHANNEL" = attr.ib(metadata=docs("The thread this event is dispatched from"))


@attr.s(slots=True)
class ThreadUpdate(ThreadCreate):
    """Dispatched when a thread is updated"""


@attr.s(slots=True)
class ThreadDelete(ThreadCreate):
    """Dispatched when a thread is deleted"""


@attr.s(slots=True)
class ThreadListSync(BaseEvent):
    """Dispatched when gaining access to a channel, contains all active threads in that channel"""

    channel_ids: List["Snowflake_Type"] = attr.ib()
    """The parent channel ids whose threads are being synced. If omitted, then threads were synced for the entire guild. This array may contain channel_ids that have no active threads as well, so you know to clear that data."""
    threads: List["BaseChannel"] = attr.ib()
    """all active threads in the given channels that the current user can access"""
    members: List["Member"] = attr.ib()
    """all thread member objects from the synced threads for the current user, indicating which threads the current user has been added to"""


@attr.s(slots=True)
class ThreadMemberUpdate(ThreadCreate):
    """Dispatched when the thread member object for the current user is updated.

    ??? info "Note from Discord"
        This event is documented for completeness, but unlikely to be used by most bots. For bots, this event largely is just a signal that you are a member of the thread
    """

    member: "Member" = attr.ib()
    """The member who was added"""


@attr.s(slots=True)
class ThreadMembersUpdate(BaseEvent):
    """Dispatched when anyone is added or removed from a thread."""

    id: "Snowflake_Type" = attr.ib()
    """The ID of the thread"""
    member_count: int = attr.ib(default=50)
    """the approximate number of members in the thread, capped at 50"""
    added_members: List["Member"] = attr.ib(factory=list)
    """Users added to the thread"""
    removed_member_ids: List["Snowflake_Type"] = attr.ib(factory=list)
    """Users removed from the thread"""


@attr.s(slots=True)
class GuildJoin(BaseEvent):
    """Dispatched when a guild is joined, created, or becomes available.

    !!! note
        This is called multiple times during startup, check the bot is ready before responding to this.
    """

    guild: "Guild" = attr.ib()
    """The guild that was created"""


@attr.s(slots=True)
class GuildUpdate(BaseEvent):
    """Dispatched when a guild is updated."""

    before: "Guild" = attr.ib()
    """Guild before this event"""
    after: "Guild" = attr.ib()
    """Guild after this event"""


@attr.s(slots=True)
class GuildLeft(BaseEvent, GuildEvent):
    """Dispatched when a guild is left"""

    guild: Optional["Guild"] = attr.ib(default=MISSING)
    """The guild, if it was cached"""


@attr.s(slots=True)
class GuildUnavailable(BaseEvent, GuildEvent):
    """Dispatched when a guild is not available."""

    guild: Optional["Guild"] = attr.ib(default=MISSING)
    """The guild, if it was cached"""


@attr.s(slots=True)
class BanCreate(BaseEvent, GuildEvent):
    """Dispatched when someone was banned from a guild"""

    user: "BaseUser" = attr.ib(metadata=docs("The user"))


@attr.s(slots=True)
class BanRemove(BanCreate):
    """Dispatched when a users ban is removed"""


@attr.s(slots=True)
class GuildEmojisUpdate(BaseEvent, GuildEvent):
    """Dispatched when a guild's emojis are updated."""

    before: List["Emoji"] = attr.ib(factory=list)
    """List of emoji before this event"""
    after: List["Emoji"] = attr.ib(factory=list)
    """List of emoji after this event"""


@attr.s(slots=True)
class GuildStickersUpdate(BaseEvent, GuildEvent):
    """Dispatched when a guild's stickers are updated."""

    before: List["Sticker"] = attr.ib(factory=list)
    """List of stickers from before this event"""
    after: List["Sticker"] = attr.ib(factory=list)
    """List of stickers from after this event"""


@attr.s(slots=True)
class MemberAdd(BaseEvent, GuildEvent):
    """Dispatched when a member is added to a guild."""

    member: "Member" = attr.ib(metadata=docs("The member who was added"))


@attr.s(slots=True)
class MemberRemove(MemberAdd):
    """Dispatched when a member is removed from a guild."""

    member: Union["Member", "User"] = attr.ib(
        metadata=docs("The member who was added, can be user if the member is not cached")
    )


@attr.s(slots=True)
class MemberUpdate(BaseEvent, GuildEvent):
    """Dispatched when a member is updated."""

    before: "Member" = attr.ib()
    """The state of the member before this event"""
    after: "Member" = attr.ib()
    """The state of the member after this event"""


@attr.s(slots=True)
class RoleCreate(BaseEvent, GuildEvent):
    """Dispatched when a role is created."""

    role: "Role" = attr.ib()
    """The created role"""


@attr.s(slots=True)
class RoleUpdate(BaseEvent, GuildEvent):
    """Dispatched when a role is updated."""

    before: "Role" = attr.ib()
    """The role before this event"""
    after: "Role" = attr.ib()
    """The role after this event"""


@attr.s(slots=True)
class RoleDelete(BaseEvent, GuildEvent):
    """Dispatched when a guild role is deleted"""

    role_id: "Snowflake_Type" = attr.ib()
    """The ID of the deleted role"""


@attr.s(slots=True)
class GuildMembersChunk(BaseEvent, GuildEvent):
    """Sent in response to Guild Request Members. You can use the `chunk_index` and `chunk_count` to calculate how many chunks are left for your request."""

    chunk_index: int = attr.ib()
    """The chunk index in the expected chunks for this response (0 <= chunk_index < chunk_count)"""
    chunk_count: int = attr.ib()
    """the total number of expected chunks for this response"""
    presences: List = attr.ib()
    """if passing true to `REQUEST_GUILD_MEMBERS`, presences of the returned members will be here"""
    nonce: str = attr.ib()
    """The nonce used in the request, if any"""
    members: List["Member"] = attr.ib(factory=list)
    """A list of members"""


@attr.s(slots=True)
class IntegrationCreate(BaseEvent):
    """Dispatched when a guild integration is created"""

    integration: "GuildIntegration" = attr.ib()


@attr.s(slots=True)
class IntegrationUpdate(IntegrationCreate):
    """Dispatched when a guild integration is updated"""


@attr.s(slots=True)
class IntegrationDelete(BaseEvent, GuildEvent):
    """Dispatched when a guild integration is deleted"""

    id: "Snowflake_Type" = attr.ib()
    """The ID of the integration"""
    application_id: "Snowflake_Type" = attr.ib(default=None)
    """The ID of the bot/application for this integration"""


@attr.s(slots=True)
class InviteCreate(BaseEvent):
    """Dispatched when a guild invite is created"""

    invite: Invite = attr.ib()


@attr.s(slots=True)
class InviteDelete(InviteCreate):
    """Dispatched when an invite is deleted"""


@attr.s(slots=True)
class MessageCreate(BaseEvent):
    """Dispatched when a message is created"""

    message: "Message" = attr.ib()


@attr.s(slots=True)
class MessageUpdate(BaseEvent):
    """Dispatched when a message is edited"""

    before: "Message" = attr.ib()
    """The message before this event was created"""
    after: "Message" = attr.ib()
    """The message after this event was created"""


@attr.s(slots=True)
class MessageDelete(BaseEvent):
    """Dispatched when a message is deleted."""

    message: "Message" = attr.ib()


@attr.s(slots=True)
class MessageDeleteBulk(BaseEvent, GuildEvent):
    """Dispatched when multiple messages are deleted at once."""

    channel_id: "Snowflake_Type" = attr.ib()
    """The ID of the channel these were deleted in"""
    ids: List["Snowflake_Type"] = attr.ib(factory=list)
    """A list of message snowflakes"""


@attr.s(slots=True)
class MessageReactionAdd(BaseEvent):
    """Dispatched when a reaction is added to a message."""

    message: "Message" = attr.ib(metadata=docs("The message that was reacted to"))
    emoji: "emoji" = attr.ib(metadata=docs("The emoji that was added to the message"))
    author: Union["Member", "User"] = attr.ib(metadata=docs("The user who added the reaction"))


@attr.s(slots=True)
class MessageReactionRemove(MessageReactionAdd):
    """Dispatched when a reaction is removed"""


@attr.s(slots=True)
class MessageReactionRemoveAll(BaseEvent, GuildEvent):
    """Dispatched when all reactions are removed from a message"""

    message: "Message" = attr.ib()
    """The message that was reacted to"""


@attr.s(slots=True)
class PresenceUpdate(BaseEvent):
    """A user's presence has changed"""

    user: "User" = attr.ib()
    """The user in question"""
    status: str = attr.ib()
    """'Either `idle`, `dnd`, `online`, or `offline`'"""
    activities: List["Activity"] = attr.ib()
    """The users current activities"""
    client_status: dict = attr.ib()
    """What platform the user is reported as being on"""
    guild_id: "Snowflake_Type" = attr.ib()
    """The guild this presence update was dispatched from"""


@attr.s(slots=True)
class StageInstanceCreate(BaseEvent):
    """Dispatched when a stage instance is created"""

    stage_instance: StageInstance = attr.ib(metadata=docs("The stage instance"))


@attr.s(slots=True)
class StageInstanceDelete(StageInstanceCreate):
    """Dispatched when a stage instance is deleted"""


@attr.s(slots=True)
class StageInstanceUpdate(StageInstanceCreate):
    """Dispatched when a stage instance is updated"""


@attr.s(slots=True)
class TypingStart(BaseEvent):
    """Dispatched when a user starts typing"""

    author: Union["User", "Member"] = attr.ib()
    """The user who started typing"""
    channel: "BaseChannel" = attr.ib()
    """The channel typing is in"""
    guild: "Guild" = attr.ib()
    """The ID of the guild this typing is in"""
    timestamp: "Timestamp" = attr.ib()
    """unix time (in seconds) of when the user started typing"""


@attr.s(slots=True)
class WebhooksUpdate(BaseEvent, GuildEvent):
    """Dispatched when a guild channel webhook is created, updated, or deleted"""

    # Discord doesnt sent the webhook object for this event, for some reason
    channel_id: "Snowflake_Type" = attr.ib()
    """The ID of the webhook was updated"""


@attr.s(slots=True)
class InteractionCreate(BaseEvent):
    """Dispatched when a user uses an Application Command"""

    interaction: dict = attr.ib()


@attr.s(slots=True)
class VoiceStateUpdate(BaseEvent):
    """Dispatched when a user joins/leaves/moves voice channels"""

    before: Optional["VoiceState"] = attr.ib()
    """The voice state before this event was created or None if the user was not in a voice channel"""
    after: Optional["VoiceState"] = attr.ib()
    """The voice state after this event was created or None if the user is no longer in a voice channel"""
