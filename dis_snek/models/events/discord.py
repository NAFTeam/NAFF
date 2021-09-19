from typing import TYPE_CHECKING, Any, List, Union

import attr

from dis_snek.models.events.internal import BaseEvent, _GuildEvent

if TYPE_CHECKING:
    from dis_snek.models.discord_objects.guild import Guild
    from dis_snek.models.discord_objects.channel import BaseChannel
    from dis_snek.models.discord_objects.message import Message
    from dis_snek.models.timestamp import Timestamp
    from dis_snek.models.discord_objects.user import Member, User, BaseUser
    from dis_snek.models.snowflake import Snowflake_Type
    from dis_snek.models.discord_objects.context import ComponentContext
    from dis_snek.models.discord_objects.emoji import Emoji
    from dis_snek.models.discord_objects.role import Role
    from dis_snek.models.discord_objects.sticker import Sticker


@attr.s()
class RawGatewayEvent(BaseEvent):
    """An event dispatched from the gateway. Holds the raw dict that the gateway dispatches"""

    data: dict = attr.ib(factory=dict)
    """Raw Data from the gateway"""


@attr.s()
class ChannelCreate(BaseEvent):
    """Dispatched when a channel is created."""

    channel: "BaseChannel" = attr.ib(metadata={"docs": "The channel this event is dispatched from"})


@attr.s()
class ChannelUpdate(ChannelCreate):
    """Dispatched when a channel is updated"""


@attr.s()
class ChannelDelete(ChannelCreate):
    """Dispatched when a channel is deleted"""


@attr.s()
class ChannelPinsUpdate(ChannelCreate):
    """Dispatched when a channel's pins are updated"""

    last_pin_timestamp: "Timestamp" = attr.ib()
    """The time at which the most recent pinned message was pinned"""


@attr.s()
class ThreadCreate(BaseEvent):
    """Dispatched when a thread is created."""

    thread: Any = attr.ib(
        metadata={"docs": "The thread this event is dispatched from"}
    )  # TODO: Replace this with a thread object type


@attr.s()
class ThreadUpdate(ThreadCreate):
    """Dispatched when a thread is updated"""


@attr.s()
class ThreadDelete(ThreadCreate):
    """Dispatched when a thread is deleted"""


@attr.s()
class ThreadListSync(BaseEvent):
    """Dispatched when gaining access to a channel, contains all active threads in that channel"""

    channel_ids: List["Snowflake_Type"] = attr.ib()
    """The parent channel ids whose threads are being synced. If omitted, then threads were synced for the entire guild. This array may contain channel_ids that have no active threads as well, so you know to clear that data."""
    threads: List["BaseChannel"] = attr.ib()
    """all active threads in the given channels that the current user can access"""
    members: List["Member"] = attr.ib()
    """all thread member objects from the synced threads for the current user, indicating which threads the current user has been added to"""


@attr.s()
class ThreadMemberUpdate(ThreadCreate):
    """Dispatched when the thread member object for the current user is updated.

    ??? info "Note from Discord"
        This event is documented for completeness, but unlikely to be used by most bots. For bots, this event largely is just a signal that you are a member of the thread
    """

    member: "Member" = attr.ib()
    """The member who was added"""


@attr.s()
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


@attr.s()
class GuildCreate(BaseEvent):
    """Dispatched when a guild is created."""

    guild: "Guild" = attr.ib()
    """The guild that was created"""


@attr.s()
class GuildUpdate(BaseEvent):
    """Dispatched when a guild is updated."""

    before: "Guild" = attr.ib()
    """Guild before this event"""
    after: "Guild" = attr.ib()
    """Guild after this event"""


@attr.s()
class GuildDelete(BaseEvent, _GuildEvent):
    """Dispatched when a guild becomes unavailable or user left/removed."""

    unavailable: bool = attr.ib(default=False)
    """If this event was triggered due to an outage"""


@attr.s()
class GuildBanAdd(BaseEvent, _GuildEvent):
    """Dispatched when someone was banned from a guild"""

    user: "BaseUser" = attr.ib(metadata={"docs": "The user"})


@attr.s()
class GuildBanRemove(GuildBanAdd):
    """Dispatched when a users ban is removed"""


@attr.s()
class GuildEmojisUpdate(BaseEvent, _GuildEvent):
    """Dispatched when a guild's emojis are updated."""

    before: List["Emoji"] = attr.ib(factory=list)
    """List of emoji before this event"""
    after: List["Emoji"] = attr.ib(factory=list)
    """List of emoji after this event"""


@attr.s()
class GuildStickersUpdate(BaseEvent, _GuildEvent):
    """Dispatched when a guild's stickers are updated."""

    before: List["Sticker"] = attr.ib(factory=list)
    """List of stickers from before this event"""
    after: List["Sticker"] = attr.ib(factory=list)
    """List of stickers from after this event"""


@attr.s()
class MemberAdd(BaseEvent, _GuildEvent):
    """Dispatched when a member is added to a guild."""

    member: "Member" = attr.ib(metadata={"docs": "The member who was added"})


@attr.s()
class MemberRemove(MemberAdd):
    """Dispatched when a member is removed from a guild."""


@attr.s()
class MemberUpdate(BaseEvent, _GuildEvent):
    """Dispatched when a member is updated."""

    # todo: It would be better to just have a member, before, and after field. but for now im mirroring the api

    before: "Member" = attr.ib()
    """The state of the member before this event"""
    after: "Member" = attr.ib()
    """The state of the member after this event"""


@attr.s()
class GuildRoleCreate(BaseEvent, _GuildEvent):
    """Dispatched when a role is created."""

    role: "Role" = attr.ib()
    """The created role"""


@attr.s()
class GuildRoleUpdate(BaseEvent, _GuildEvent):
    """Dispatched when a role is updated."""

    before: "Role" = attr.ib()
    """The role before this event"""
    after: "Role" = attr.ib()
    """The role after this event"""


@attr.s()
class GuildRoleDelete(BaseEvent, _GuildEvent):
    """Dispatched when a guild role is deleted"""

    role_id: "Snowflake_Type" = attr.ib()
    """The ID of the deleted role"""


@attr.s()
class GuildMembersChunk(BaseEvent, _GuildEvent):
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


@attr.s()
class IntegrationCreate(BaseEvent):
    """Dispatched when a guild integration is created"""

    integration: Any = attr.ib()  # TODO: Replace this with a integration object type


@attr.s()
class IntegrationUpdate(BaseEvent, _GuildEvent):
    """Dispatched when a guild integration is updated"""

    before: Any = attr.ib()  # TODO: Replace this with a integration object type
    """The integration before this event"""
    after: Any = attr.ib()  # TODO: Replace this with a integration object type
    """The integration after this event"""


@attr.s()
class IntegrationDelete(BaseEvent, _GuildEvent):
    """Dispatched when a guild integration is deleted"""

    id: "Snowflake_Type" = attr.ib()
    """The ID of the integration"""
    application_id: "Snowflake_Type" = attr.ib(default=None)
    """The ID of the bot/application for this integration"""


@attr.s()
class GuildIntegrationsUpdate(BaseEvent, _GuildEvent):
    """Dispatched when a guild integration is updated"""


@attr.s()
class InviteCreate(BaseEvent):
    """Dispatched when a guild invite is created"""

    invite: Any = attr.ib()  # TODO: Replace this with a invite object type


@attr.s()
class MessageCreate(BaseEvent):
    """Dispatched when a message is created"""

    message: "Message" = attr.ib()


@attr.s()
class MessageUpdate(BaseEvent):
    """Dispatched when a message is edited"""

    before: "Message" = attr.ib()
    """The message before this event was created"""
    after: "Message" = attr.ib()
    """The message after this event was created"""


@attr.s()
class MessageDelete(BaseEvent):
    """Dispatched when a message is deleted."""

    message: "Message" = attr.ib()


@attr.s()
class MessageDeleteBulk(BaseEvent, _GuildEvent):
    """Dispatched when multiple messages are deleted at once."""

    channel_id: "Snowflake_Type" = attr.ib()
    """The ID of the channel these were deleted in"""
    ids: List["Snowflake_Type"] = attr.ib(factory=list)
    """A list of message snowflakes"""


@attr.s()
class MessageReactionAdd(BaseEvent):
    """Dispatched when a reaction is added to a message."""

    message: "Message" = attr.ib(metadata={"docs": "The message that was reacted to"})
    emoji: "emoji" = attr.ib(metadata={"docs": "The emoji that was added to the message"})
    author: Union["Member", "User"] = attr.ib(metadata={"docs": "The user who added the reaction"})


@attr.s()
class MessageReactionRemove(MessageReactionAdd):
    """Dispatched when a reaction is removed"""


@attr.s()
class MessageReactionRemoveAll(BaseEvent, _GuildEvent):
    """Dispatched when all reactions are removed from a message"""

    message: "Message" = attr.ib()
    """The message that was reacted to"""


@attr.s()
class PresenceUpdate(BaseEvent):
    """A user's presence has changed"""

    user: "User" = attr.ib()
    """The user in question"""
    status: str = attr.ib()
    """'Either `idle`, `dnd`, `online`, or `offline`'"""
    activities: List = attr.ib()
    """The users current activities"""
    client_status: dict = attr.ib()
    """What platform the user is reported as being on"""


@attr.s()
class StageInstanceCreate(BaseEvent):
    """Dispatched when a stage instance is created"""

    stage_instance: Any = attr.ib(
        metadata={"docs": "The stage instance"}
    )  # TODO: Replace this with a stage instance object type.


@attr.s()
class StageInstanceDelete(StageInstanceCreate):
    """Dispatched when a stage instance is deleted"""


@attr.s()
class StageInstanceUpdate(BaseEvent):
    """Dispatched when a stage instance is updated"""

    before: Any = attr.ib()  # TODO: Replace this
    """The stage instance before this event was created"""
    after: Any = attr.ib()  # TODO: Replace this
    """The stage instance after this event was created"""


@attr.s()
class TypingStart(BaseEvent):
    """Dispatched when a user starts typing"""

    channel: "BaseChannel" = attr.ib()
    """The channel typing is in"""
    guild_id: "Snowflake_Type" = attr.ib()
    """The ID of the guild this typing is in"""
    user_id: "Snowflake_Type" = attr.ib()
    """The ID of the user who is typing"""
    timestamp: "Timestamp" = attr.ib()
    """unix time (in seconds) of when the user started typing"""
    member: "Member" = attr.ib()
    """The member who started typing, if this is in a guild"""


@attr.s()
class WebhooksUpdate(BaseEvent, _GuildEvent):
    """Dispatched when a guild channel webhook is created, updated, or deleted"""

    # Discord doesnt sent the webhook object for this event, for some reason
    channel_id: "Snowflake_Type" = attr.ib()
    """The ID of the webhook was updated"""


@attr.s()
class InteractionCreate(BaseEvent):
    """Dispatched when a user uses an Application Command"""

    interaction: dict = attr.ib()
