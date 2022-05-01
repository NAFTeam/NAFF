import logging
from enum import Enum, EnumMeta, IntEnum, IntFlag, _decompose
from functools import reduce
from operator import or_
from typing import Iterator, Tuple

from dis_snek.client.const import logger_name

_log = logging.getLogger(logger_name)

__all__ = (
    "WebSocketOPCodes",
    "Intents",
    "UserFlags",
    "ApplicationFlags",
    "TeamMembershipState",
    "PremiumTypes",
    "MessageTypes",
    "MessageActivityTypes",
    "MessageFlags",
    "Permissions",
    "ChannelTypes",
    "ComponentTypes",
    "CommandTypes",
    "InteractionTypes",
    "ButtonStyles",
    "MentionTypes",
    "OverwriteTypes",
    "DefaultNotificationLevels",
    "ExplicitContentFilterLevels",
    "MFALevels",
    "VerificationLevels",
    "NSFWLevels",
    "PremiumTiers",
    "SystemChannelFlags",
    "VideoQualityModes",
    "AutoArchiveDuration",
    "ActivityType",
    "ActivityFlags",
    "Status",
    "StagePrivacyLevel",
    "IntegrationExpireBehaviour",
    "InviteTargetTypes",
    "ScheduledEventPrivacyLevel",
    "ScheduledEventType",
    "ScheduledEventStatus",
    "AuditLogEventType",
)


class AntiFlag:
    def __init__(self, anti=0) -> None:
        self.anti = anti

    def __get__(self, instance, cls) -> int:
        negative = ~cls(self.anti)
        positive = cls(reduce(or_, negative))
        return positive


def _distinct(source) -> Tuple:
    return (x for x in source if (x.value & (x.value - 1)) == 0 and x.value != 0)


class DistinctFlag(EnumMeta):
    def __iter__(cls) -> Iterator:
        yield from _distinct(super().__iter__())

    def __call__(cls, value, names=None, *, module=None, qualname=None, type=None, start=1) -> "DistinctFlag":
        # To automatically convert string values into ints (eg for permissions)
        return super().__call__(int(value), names, module=module, qualname=qualname, type=type, start=start)


class DiscordIntFlag(IntFlag, metaclass=DistinctFlag):
    def __iter__(self) -> Iterator:
        yield from _decompose(self.__class__, self)[0]


class WebSocketOPCodes(IntEnum):
    """Codes used by the Gateway to signify events."""

    DISPATCH = 0
    """An event was dispatched"""
    HEARTBEAT = 1
    """Fired periodically by the client to keep the connection alive"""
    IDENTIFY = 2
    """Starts a new session during the initial handshake."""
    PRESENCE = 3
    """Update the client's presence."""
    VOICE_STATE = 4
    """Used to join/leave or move between voice channels."""
    VOICE_PING = 5
    RESUME = 6
    """Resume a previous session that was disconnected."""
    RECONNECT = 7
    """You should attempt to reconnect and resume immediately."""
    REQUEST_MEMBERS = 8
    """Request information about offline guild members in a large guild."""
    INVALIDATE_SESSION = 9
    """The session has been invalidated. You should reconnect and identify/resume accordingly."""
    HELLO = 10
    """Sent immediately after connecting, contains the `heartbeat_interval` to use."""
    HEARTBEAT_ACK = 11
    """Sent in response to receiving a heartbeat to acknowledge that it has been received."""
    GUILD_SYNC = 12


class Intents(DiscordIntFlag):  # type: ignore
    """
    When identifying to the gateway, you can specify an intents parameter which allows you to conditionally subscribe to pre-defined "intents", groups of events defined by Discord.

    info:
        For details about what intents do, or which intents you'll want, please read the [Discord API Documentation](https://discord.com/developers/docs/topics/gateway#gateway-intents)

    """

    GUILDS = 1 << 0
    GUILD_MEMBERS = 1 << 1
    GUILD_BANS = 1 << 2
    GUILD_EMOJIS_AND_STICKERS = 1 << 3
    GUILD_INTEGRATIONS = 1 << 4
    GUILD_WEBHOOKS = 1 << 5
    GUILD_INVITES = 1 << 6
    GUILD_VOICE_STATES = 1 << 7
    GUILD_PRESENCES = 1 << 8
    GUILD_MESSAGES = 1 << 9
    GUILD_MESSAGE_REACTIONS = 1 << 10
    GUILD_MESSAGE_TYPING = 1 << 11
    DIRECT_MESSAGES = 1 << 12
    DIRECT_MESSAGE_REACTIONS = 1 << 13
    DIRECT_MESSAGE_TYPING = 1 << 14
    GUILD_MESSAGE_CONTENT = 1 << 15
    GUILD_SCHEDULED_EVENTS = 1 << 16

    # Shortcuts/grouping/aliases
    MESSAGES = GUILD_MESSAGES | DIRECT_MESSAGES
    REACTIONS = GUILD_MESSAGE_REACTIONS | DIRECT_MESSAGE_REACTIONS
    TYPING = GUILD_MESSAGE_TYPING | DIRECT_MESSAGE_TYPING

    PRIVILEGED = GUILD_PRESENCES | GUILD_MEMBERS | GUILD_MESSAGE_CONTENT
    NON_PRIVILEGED = AntiFlag(PRIVILEGED)
    DEFAULT = NON_PRIVILEGED

    # Special members
    NONE = 0
    ALL = AntiFlag()

    @classmethod
    def new(
        cls,
        guilds=False,
        guild_members=False,
        guild_bans=False,
        guild_emojis_and_stickers=False,
        guild_integrations=False,
        guild_webhooks=False,
        guild_invites=False,
        guild_voice_states=False,
        guild_presences=False,
        guild_messages=False,
        guild_message_reactions=False,
        guild_message_typing=False,
        direct_messages=False,
        direct_message_reactions=False,
        direct_message_typing=False,
        guild_message_content=False,
        guild_scheduled_events=False,
        messages=False,
        reactions=False,
        typing=False,
        privileged=False,
        non_privileged=False,
        default=True,
        all=False,
    ) -> "Intents":
        """Set your desired intents."""
        kwargs = locals()
        del kwargs["cls"]

        intents = cls.NONE
        for key in kwargs:
            if kwargs[key]:
                intents |= getattr(cls, key.upper())
        return intents


class UserFlags(DiscordIntFlag):  # type: ignore
    """Flags a user can have."""

    DISCORD_EMPLOYEE = 1 << 0
    """This person works for Discord"""
    PARTNERED_SERVER_OWNER = 1 << 1
    """User owns a partnered server"""
    HYPESQUAD_EVENTS = 1 << 2
    """User has helped with a hypesquad event"""
    BUG_HUNTER_LEVEL_1 = 1 << 3
    """User has passed the bug hunters quiz"""

    HOUSE_BRAVERY = 1 << 6
    """User belongs to the `bravery` house"""
    HOUSE_BRILLIANCE = 1 << 7
    """User belongs to the `brilliance` house"""
    HOUSE_BALANCE = 1 << 8
    """User belongs to the `balance` house"""
    EARLY_SUPPORTER = 1 << 9
    """This person had Nitro prior to Wednesday, October 10th, 2018"""

    TEAM_USER = 1 << 10
    """A team user"""

    BUG_HUNTER_LEVEL_2 = 1 << 14
    """User is a bug hunter level 2"""

    VERIFIED_BOT = 1 << 16
    """This bot has been verified by Discord"""
    EARLY_VERIFIED_BOT_DEVELOPER = 1 << 17
    """This user was one of the first to be verified"""
    DISCORD_CERTIFIED_MODERATOR = 1 << 18
    """This user is a certified moderator"""

    # Shortcuts/grouping/aliases
    HYPESQUAD = HOUSE_BRAVERY | HOUSE_BRILLIANCE | HOUSE_BALANCE
    BUG_HUNTER = BUG_HUNTER_LEVEL_1 | BUG_HUNTER_LEVEL_2

    # Special members
    NONE = 0
    ALL = AntiFlag()


class ApplicationFlags(DiscordIntFlag):  # type: ignore
    """Flags an application can have."""

    # Flags defined by the Discord API
    GATEWAY_PRESENCE = 1 << 12
    """Verified to use presence intent"""
    GATEWAY_PRESENCE_LIMITED = 1 << 13
    """Using presence intent, without verification"""
    GATEWAY_GUILD_MEMBERS = 1 << 14
    """Verified to use guild members intent"""
    GATEWAY_GUILD_MEMBERS_LIMITED = 1 << 15
    """Using members intent, without verification"""
    VERIFICATION_PENDING_GUILD_LIMIT = 1 << 16
    """Bot has hit guild limit, and has not been successfully verified"""
    EMBEDDED = 1 << 17
    """Application is a voice channel activity (ie YouTube Together)"""


class TeamMembershipState(IntEnum):
    """Status of membership in the team."""

    INVITED = 1
    ACCEPTED = 2


class PremiumTypes(IntEnum):
    """Types of premium membership."""

    NONE = 0
    """No premium membership"""
    NITRO_CLASSIC = 1
    """Using Nitro Classic"""
    NITRO = 2
    """Full Nitro membership"""


class MessageTypes(IntEnum):
    """Types of message."""

    DEFAULT = 0
    RECIPIENT_ADD = 1
    RECIPIENT_REMOVE = 2
    CALL = 3
    CHANNEL_NAME_CHANGE = 4
    CHANNEL_ICON_CHANGE = 5
    CHANNEL_PINNED_MESSAGE = 6
    GUILD_MEMBER_JOIN = 7
    USER_PREMIUM_GUILD_SUBSCRIPTION = 8
    USER_PREMIUM_GUILD_SUBSCRIPTION_TIER_1 = 9
    USER_PREMIUM_GUILD_SUBSCRIPTION_TIER_2 = 10
    USER_PREMIUM_GUILD_SUBSCRIPTION_TIER_3 = 11
    CHANNEL_FOLLOW_ADD = 12
    GUILD_DISCOVERY_DISQUALIFIED = 14
    GUILD_DISCOVERY_REQUALIFIED = 15
    GUILD_DISCOVERY_GRACE_PERIOD_INITIAL_WARNING = 16
    GUILD_DISCOVERY_GRACE_PERIOD_FINAL_WARNING = 17
    THREAD_CREATED = 18
    REPLY = 19
    APPLICATION_COMMAND = 20
    THREAD_STARTER_MESSAGE = 21
    GUILD_INVITE_REMINDER = 22
    CONTEXT_MENU_COMMAND = 23
    AUTO_MOD = 24


class MessageActivityTypes(IntEnum):
    """An activity object, similar to an embed."""

    JOIN = 1
    """Join the event"""
    SPECTATE = 2
    """Watch the event"""
    LISTEN = 3
    """Listen along to the event"""
    JOIN_REQUEST = 5
    """Asking a user to join the activity"""


class MessageFlags(DiscordIntFlag):  # type: ignore
    """Message flags."""

    CROSSPOSTED = 1 << 0
    """This message has been published to subscribed channels (via Channel Following)"""
    IS_CROSSPOST = 1 << 1
    """This message originated from a message in another channel (via Channel Following)"""
    SUPPRESS_EMBEDS = 1 << 2
    """Do not include any embeds when serializing this message"""
    SOURCE_MESSAGE_DELETED = 1 << 3
    """The source message for this crosspost has been deleted (via Channel Following)"""
    URGENT = 1 << 4
    """This message came from the urgent message system"""
    HAS_THREAD = 1 << 5
    """This message has an associated thread, with the same id as the message"""
    EPHEMERAL = 1 << 6
    """This message is only visible to the user who invoked the Interaction"""
    LOADING = 1 << 7
    """This message is an Interaction Response and the bot is "thinking"""
    FAILED_TO_MENTION_SOME_ROLES_IN_THREAD = 1 << 8
    """This message failed to mention some roles and add their members to the thread"""

    # Special members
    NONE = 0
    ALL = AntiFlag()


class Permissions(DiscordIntFlag):  # type: ignore
    """Permissions a user or role may have."""

    # Permissions defined by Discord API
    CREATE_INSTANT_INVITE = 1 << 0
    """Allows creation of instant invites"""
    KICK_MEMBERS = 1 << 1
    """Allows kicking members"""
    BAN_MEMBERS = 1 << 2
    """Allows banning members"""
    ADMINISTRATOR = 1 << 3
    """Allows all permissions and bypasses channel permission overwrites"""
    MANAGE_CHANNELS = 1 << 4
    """Allows management and editing of channels"""
    MANAGE_GUILD = 1 << 5
    """Allows management and editing of the guild"""
    ADD_REACTIONS = 1 << 6
    """Allows for the addition of reactions to messages"""
    VIEW_AUDIT_LOG = 1 << 7
    """Allows for viewing of audit logs"""
    PRIORITY_SPEAKER = 1 << 8
    """Allows for using priority speaker in a voice channel"""
    STREAM = 1 << 9
    """Allows the user to go live"""
    VIEW_CHANNEL = 1 << 10
    """Allows guild members to view a channel, which includes reading messages in text channels and joining voice channels"""
    SEND_MESSAGES = 1 << 11
    """	Allows for sending messages in a channel (does not allow sending messages in threads)"""
    SEND_TTS_MESSAGES = 1 << 12
    """	Allows for sending of `/tts` messages"""
    MANAGE_MESSAGES = 1 << 13
    """Allows for deletion of other users messages"""
    EMBED_LINKS = 1 << 14
    """Links sent by users with this permission will be auto-embedded"""
    ATTACH_FILES = 1 << 15
    """Allows for uploading images and files"""
    READ_MESSAGE_HISTORY = 1 << 16
    """Allows for reading of message history"""
    MENTION_EVERYONE = 1 << 17
    """Allows for using the `@everyone` tag to notify all users in a channel, and the `@here` tag to notify all online users in a channel"""
    USE_EXTERNAL_EMOJIS = 1 << 18
    """Allows the usage of custom emojis from other servers"""
    VIEW_GUILD_INSIGHTS = 1 << 19
    """Allows for viewing guild insights"""
    CONNECT = 1 << 20
    """Allows for joining of a voice channel"""
    SPEAK = 1 << 21
    """Allows for speaking in a voice channel"""
    MUTE_MEMBERS = 1 << 22
    """Allows for muting members in a voice channel"""
    DEAFEN_MEMBERS = 1 << 23
    """Allows for deafening of members in a voice channel"""
    MOVE_MEMBERS = 1 << 24
    """Allows for moving of members between voice channels"""
    USE_VAD = 1 << 25
    """Allows for using voice-activity-detection in a voice channel"""
    CHANGE_NICKNAME = 1 << 26
    """Allows for modification of own nickname"""
    MANAGE_NICKNAMES = 1 << 27
    """Allows for modification of other users nicknames"""
    MANAGE_ROLES = 1 << 28
    """Allows management and editing of roles"""
    MANAGE_WEBHOOKS = 1 << 29
    """Allows management and editing of webhooks"""
    MANAGE_EMOJIS_AND_STICKERS = 1 << 30
    """Allows management and editing of emojis and stickers"""
    USE_APPLICATION_COMMANDS = 1 << 31
    """Allows members to use application commands, including slash commands and context menu commands"""
    REQUEST_TO_SPEAK = 1 << 32
    """Allows for requesting to speak in stage channels. (This permission is under active development and may be changed or removed.)"""
    MANAGE_EVENTS = 1 << 33
    """Allows for creating, editing, and deleting scheduled events"""
    MANAGE_THREADS = 1 << 34
    """Allows for deleting and archiving threads, and viewing all private threads"""
    USE_PUBLIC_THREADS = 1 << 35
    """	Allows for creating public and announcement threads"""
    USE_PRIVATE_THREADS = 1 << 36
    """Allows for creating private threads"""
    USE_EXTERNAL_STICKERS = 1 << 37
    """Allows the usage of custom stickers from other servers"""
    SEND_MESSAGES_IN_THREADS = 1 << 38
    """Allows for sending messages in threads"""
    START_EMBEDDED_ACTIVITIES = 1 << 39
    """Allows for using Activities (applications with the `EMBEDDED` flag) in a voice channel"""
    MODERATE_MEMBERS = 1 << 40
    """Allows for timing out users to prevent them from sending or reacting to messages in chat and threads, and from speaking in voice and stage channels"""

    # Shortcuts/grouping/aliases
    REQUIRES_MFA = (
        KICK_MEMBERS
        | BAN_MEMBERS
        | ADMINISTRATOR
        | MANAGE_CHANNELS
        | MANAGE_GUILD
        | MANAGE_MESSAGES
        | MANAGE_ROLES
        | MANAGE_WEBHOOKS
        | MANAGE_EMOJIS_AND_STICKERS
        | MANAGE_THREADS
        | MODERATE_MEMBERS
    )
    USE_SLASH_COMMANDS = USE_APPLICATION_COMMANDS
    """Legacy alias for :attr:`USE_APPLICATION_COMMANDS`"""

    # Special members
    NONE = 0
    ALL = AntiFlag()


class ChannelTypes(IntEnum):
    """Types of channel."""

    GUILD_TEXT = 0
    """Text channel within a server"""
    DM = 1
    """Direct message between users"""
    GUILD_VOICE = 2
    """Voice channel within a server"""
    GROUP_DM = 3
    """Direct message between multiple users"""
    GUILD_CATEGORY = 4
    """Organizational category that contains up to 50 channels"""
    GUILD_NEWS = 5
    """Channel that users can follow and crosspost into their own server"""
    GUILD_NEWS_THREAD = 10
    """Temporary sub-channel within a GUILD_NEWS channel"""
    GUILD_PUBLIC_THREAD = 11
    """Temporary sub-channel within a GUILD_TEXT channel"""
    GUILD_PRIVATE_THREAD = 12
    """Temporary sub-channel within a GUILD_TEXT channel that is only viewable by those invited and those with the MANAGE_THREADS permission"""
    GUILD_STAGE_VOICE = 13
    """Voice channel for hosting events with an audience"""

    @classmethod
    def converter(cls, value) -> "ChannelTypes":
        """A converter to handle discord creating new channel types that the lib isn't aware of, without losing type info"""
        try:
            out = cls(value)
            return out
        except ValueError:
            # construct a new enum item to represent this new unknown type - without losing the value
            new = int.__new__(cls)
            new._name_ = f"UNKNOWN-TYPE-{value}"
            new._value_ = value

            return cls._value2member_map_.setdefault(value, new)

    @property
    def guild(self) -> bool:
        """Whether this channel is a guild channel."""
        return self.value not in {1, 3}

    @property
    def voice(self) -> bool:
        """Whether this channel is a voice channel."""
        return self.value in {2, 13}


class ComponentTypes(IntEnum):
    """The types of components supported by discord."""

    ACTION_ROW = 1
    """Container for other components"""
    BUTTON = 2
    """Button object"""
    SELECT = 3
    """Select menu for picking from choices"""
    INPUT_TEXT = 4
    """Text input object"""


class CommandTypes(IntEnum):
    """The interaction commands supported by discord."""

    CHAT_INPUT = 1
    """Slash commands; a text-based command that shows up when a user types `/`"""
    USER = 2
    """A UI-based command that shows up when you right click or tap on a user"""
    MESSAGE = 3
    """A UI-based command that shows up when you right click or tap on a message"""


class InteractionTypes(IntEnum):
    """The type of interaction received by discord."""

    PING = 1
    APPLICATION_COMMAND = 2
    MESSAGE_COMPONENT = 3
    AUTOCOMPLETE = 4
    MODAL_RESPONSE = 5


class ButtonStyles(IntEnum):
    """The styles of buttons supported."""

    # Based on discord api
    PRIMARY = 1
    """blurple"""
    SECONDARY = 2
    """grey"""
    SUCCESS = 3
    """green"""
    DANGER = 4
    """red"""
    LINK = 5
    """url button"""

    # Aliases
    BLUE = 1
    BLURPLE = 1
    GRAY = 2
    GREY = 2
    GREEN = 3
    RED = 4
    URL = 5


class MentionTypes(str, Enum):
    """Types of mention."""

    EVERYONE = "everyone"
    ROLES = "roles"
    USERS = "users"


class OverwriteTypes(IntEnum):
    """Types of permission overwrite."""

    ROLE = 0
    MEMBER = 1


class DefaultNotificationLevels(IntEnum):
    """Default Notification levels for dms and guilds."""

    ALL_MESSAGES = 0
    ONLY_MENTIONS = 1


class ExplicitContentFilterLevels(IntEnum):
    """Automatic filtering of explicit content."""

    DISABLED = 0
    MEMBERS_WITHOUT_ROLES = 1
    ALL_MEMBERS = 2


class MFALevels(IntEnum):
    """Does the user use 2FA."""

    NONE = 0
    ELEVATED = 1


class VerificationLevels(IntEnum):
    """Levels of verification needed by a guild."""

    NONE = 0
    """No verification needed"""
    LOW = 1
    """Must have a verified email on their Discord Account"""
    MEDIUM = 2
    """Must also be registered on Discord for longer than 5 minutes"""
    HIGH = 3
    """Must also be a member of this server for longer than 10 minutes"""
    VERY_HIGH = 4
    """Must have a verified phone number on their Discord Account"""


class NSFWLevels(IntEnum):
    """A guilds NSFW Level."""

    DEFAULT = 0
    EXPLICIT = 1
    SAFE = 2
    AGE_RESTRICTED = 3


class PremiumTiers(IntEnum):
    """The boost level of a server."""

    NONE = 0
    """Guild has not unlocked any Server Boost perks"""
    TIER_1 = 1
    """Guild has unlocked Tier 1 Server Boost perks"""
    TIER_2 = 2
    """Guild has unlocked Tier 2 Server Boost perks"""
    TIER_3 = 3
    """Guild has unlocked Tier 3 Server Boost perks"""


class SystemChannelFlags(DiscordIntFlag):
    """System channel settings."""

    SUPPRESS_JOIN_NOTIFICATIONS = 1 << 0
    """Suppress member join notifications"""
    SUPPRESS_PREMIUM_SUBSCRIPTIONS = 1 << 1
    """Suppress server boost notifications"""
    SUPPRESS_GUILD_REMINDER_NOTIFICATIONS = 1 << 2
    """Suppress server setup tips"""
    SUPPRESS_JOIN_NOTIFICATION_REPLIES = 1 << 3
    """Hide member join sticker reply buttons"""

    # Special members
    NONE = 0
    ALL = AntiFlag()


class VideoQualityModes(IntEnum):
    """Video quality settings."""

    AUTO = 1
    FULL = 2


class AutoArchiveDuration(IntEnum):
    """Thread archive duration, in minutes."""

    ONE_HOUR = 60
    ONE_DAY = 1440
    THREE_DAY = 4320
    ONE_WEEK = 10080


class ActivityType(IntEnum):
    """
    The types of presence activity that can be used in presences.

    !!! note     Only `GAME` `STREAMING` `LISTENING` `WATCHING` and
    `COMPETING` are usable by bots

    """

    GAME = 0
    """Playing {name}; Example: Playing Rocket League"""
    STREAMING = 1
    """Streaming {details}; Example: Streaming Rocket League"""
    LISTENING = 2
    """Listening to {name}; Example: Listening to Spotify"""
    WATCHING = 3
    """Watching {name}; Example: Watching YouTube Together"""
    CUSTOM = 4
    """{emoji} {name}; Example: :smiley: I am cool"""
    COMPETING = 5
    """Competing in {name}; Example: Competing in Arena World Champions"""

    PLAYING = GAME
    """Alias for `GAME`"""


class ActivityFlags(DiscordIntFlag):
    INSTANCE = 1 << 0
    JOIN = 1 << 1
    SPECTATE = 1 << 2
    JOIN_REQUEST = 1 << 3
    SYNC = 1 << 4
    PLAY = 1 << 5
    PARTY_PRIVACY_FRIENDS = 1 << 6
    PARTY_PRIVACY_VOICE_CHANNEL = 1 << 7
    EMBEDDED = 1 << 8


class Status(str, Enum):
    """Represents the statuses a user may have."""

    ONLINE = "online"
    OFFLINE = "offline"
    DND = "dnd"
    IDLE = "idle"
    INVISIBLE = "invisible"

    AFK = IDLE
    DO_NOT_DISTURB = DND


class StagePrivacyLevel(IntEnum):
    PUBLIC = 1
    GUILD_ONLY = 2


class IntegrationExpireBehaviour(IntEnum):
    REMOVE_ROLE = 0
    KICK = 1


class InviteTargetTypes(IntEnum):
    STREAM = 1
    EMBEDDED_APPLICATION = 2


class ScheduledEventPrivacyLevel(IntEnum):
    """The privacy level of the scheduled event."""

    GUILD_ONLY = 2


class ScheduledEventType(IntEnum):
    """The type of entity that the scheduled event is attached to."""

    STAGE_INSTANCE = 1
    """ Stage Channel """
    VOICE = 2
    """ Voice Channel """
    EXTERNAL = 3
    """ External URL """


class ScheduledEventStatus(IntEnum):
    """The status of the scheduled event."""

    SCHEDULED = 1
    ACTIVE = 2
    COMPLETED = 3
    CANCELED = 4


class AuditLogEventType(IntEnum):
    """The type of audit log entry type"""

    GUILD_UPDATE = 1
    CHANNEL_CREATE = 10
    CHANNEL_UPDATE = 11
    CHANNEL_DELETE = 12
    CHANNEL_OVERWRITE_CREATE = 13
    CHANNEL_OVERWRITE_UPDATE = 14
    CHANNEL_OVERWRITE_DELETE = 15
    MEMBER_KICK = 20
    MEMBER_PRUNE = 21
    MEMBER_BAN_ADD = 22
    MEMBER_BAN_REMOVE = 23
    MEMBER_UPDATE = 24
    MEMBER_ROLE_UPDATE = 25
    MEMBER_MOVE = 26
    MEMBER_DISCONNECT = 27
    BOT_ADD = 28
    ROLE_CREATE = 30
    ROLE_UPDATE = 31
    ROLE_DELETE = 32
    INVITE_CREATE = 40
    INVITE_UPDATE = 41
    INVITE_DELETE = 42
    WEBHOOK_CREATE = 50
    WEBHOOK_UPDATE = 51
    WEBHOOK_DELETE = 52
    EMOJI_CREATE = 60
    EMOJI_UPDATE = 61
    EMOJI_DELETE = 62
    MESSAGE_DELETE = 72
    MESSAGE_BULK_DELETE = 73
    MESSAGE_PIN = 74
    MESSAGE_UNPIN = 75
    INTEGRATION_CREATE = 80
    INTEGRATION_UPDATE = 81
    INTEGRATION_DELETE = 82
    STAGE_INSTANCE_CREATE = 83
    STAGE_INSTANCE_UPDATE = 84
    STAGE_INSTANCE_DELETE = 85
    STICKER_CREATE = 90
    STICKER_UPDATE = 91
    STICKER_DELETE = 92
    GUILD_SCHEDULED_EVENT_CREATE = 100
    GUILD_SCHEDULED_EVENT_UPDATE = 101
    GUILD_SCHEDULED_EVENT_DELETE = 102
    THREAD_CREATE = 110
    THREAD_UPDATE = 111
    THREAD_DELETE = 112
