import logging
from enum import Enum, EnumMeta, IntEnum, IntFlag, _decompose
from functools import reduce
from operator import or_
from typing import Tuple

from dis_snek.const import logger_name

_log = logging.getLogger(logger_name)


class AntiFlag:
    def __init__(self, anti=0):
        self.anti = anti

    def __get__(self, instance, cls):
        negative = ~cls(self.anti)
        positive = cls(reduce(or_, negative))
        return positive


def _distinct(source) -> Tuple:
    return (x for x in source if (x.value & (x.value - 1)) == 0 and x.value != 0)


class DistinctFlag(EnumMeta):
    def __iter__(cls):
        yield from _distinct(super().__iter__())

    def __call__(cls, value, names=None, *, module=None, qualname=None, type=None, start=1):
        # To automatically convert string values into ints (eg for permissions)
        return super().__call__(int(value), names, module=module, qualname=qualname, type=type, start=start)


class DiscordIntFlag(IntFlag, metaclass=DistinctFlag):
    def __iter__(self):
        yield from _decompose(self.__class__, self)[0]


class WebSocketOPCodes(IntEnum):
    """Codes used by the Gateway to signify events"""

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
    """When identifying to the gateway, you can specify an intents parameter which allows you to conditionally subscribe to pre-defined "intents", groups of events defined by Discord.

    info:
        For details about what intents do, or which intents you'll want, please read the [Discord API Documentation](https://discord.com/developers/docs/topics/gateway#gateway-intents)"""

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

    # Shortcuts/grouping/aliases
    MESSAGES = GUILD_MESSAGES | DIRECT_MESSAGES
    REACTIONS = GUILD_MESSAGE_REACTIONS | DIRECT_MESSAGE_REACTIONS
    TYPING = GUILD_MESSAGE_TYPING | DIRECT_MESSAGE_TYPING

    PRIVILEGED = GUILD_PRESENCES | GUILD_MEMBERS
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
        messages=False,
        reactions=False,
        typing=False,
        privileged=False,
        non_privileged=False,
        default=True,
        all=False,
    ):
        """
        Set your desired intents
        """
        kwargs = locals()
        del kwargs["cls"]

        intents = cls.NONE
        for key in kwargs:
            if kwargs[key]:
                intents |= getattr(cls, key.upper())
        return intents


class UserFlags(DiscordIntFlag):  # type: ignore
    """Flags a user can have"""

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
    """This person had Nitro prior to prior to Wednesday, October 10th, 2018"""

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
    """Flags an application can have"""

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
    """Self explanatory"""

    INVITED = 1
    ACCEPTED = 2


class PremiumTypes(IntEnum):
    """Types of premium membership"""

    NONE = 0
    """No premium membership"""
    NITRO_CLASSIC = 1
    """Using Nitro Classic"""
    NITRO = 2
    """Full Nitro membership"""


class MessageTypes(IntEnum):
    """Types of message"""

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


class MessageActivityTypes(IntEnum):
    """An activity object, similar to an embed"""

    JOIN = 1
    """Join the event"""
    SPECTATE = 2
    """Watch the event"""
    LISTEN = 3
    """Listen along to the event"""
    JOIN_REQUEST = 5
    """Asking a user to join the activity"""


class MessageFlags(DiscordIntFlag):  # type: ignore
    """Message flags"""

    CROSSPOSTED = 1 << 0
    IS_CROSSPOST = 1 << 1
    SUPPRESS_EMBEDS = 1 << 2
    SOURCE_MESSAGE_DELETED = 1 << 3
    URGENT = 1 << 4
    HAS_THREAD = 1 << 5
    EPHEMERAL = 1 << 6
    LOADING = 1 << 7

    # Special members
    NONE = 0
    ALL = AntiFlag()


class Permissions(DiscordIntFlag):  # type: ignore
    """Permissions a user or role may have"""

    # Permissions defined by Discord API
    CREATE_INSTANT_INVITE = 1 << 0
    KICK_MEMBERS = 1 << 1
    BAN_MEMBERS = 1 << 2
    ADMINISTRATOR = 1 << 3
    MANAGE_CHANNELS = 1 << 4
    MANAGE_GUILD = 1 << 5
    ADD_REACTIONS = 1 << 6
    VIEW_AUDIT_LOG = 1 << 7
    PRIORITY_SPEAKER = 1 << 8
    STREAM = 1 << 9
    VIEW_CHANNEL = 1 << 10
    SEND_MESSAGES = 1 << 11
    SEND_TTS_MESSAGES = 1 << 12
    MANAGE_MESSAGES = 1 << 13
    EMBED_LINKS = 1 << 14
    ATTACH_FILES = 1 << 15
    READ_MESSAGE_HISTORY = 1 << 16
    MENTION_EVERYONE = 1 << 17
    USE_EXTERNAL_EMOJIS = 1 << 18
    VIEW_GUILD_INSIGHTS = 1 << 19
    CONNECT = 1 << 20
    SPEAK = 1 << 21
    MUTE_MEMBERS = 1 << 22
    DEAFEN_MEMBERS = 1 << 23
    MOVE_MEMBERS = 1 << 24
    USE_VAD = 1 << 25
    CHANGE_NICKNAME = 1 << 26
    MANAGE_NICKNAMES = 1 << 27
    MANAGE_ROLES = 1 << 28
    MANAGE_WEBHOOKS = 1 << 29
    MANAGE_EMOJIS_AND_STICKERS = 1 << 30
    USE_SLASH_COMMANDS = 1 << 31
    REQUEST_TO_SPEAK = 1 << 32  # This permission is under active development and may be changed or removed.
    MANAGE_THREADS = 1 << 34
    USE_PUBLIC_THREADS = 1 << 35
    USE_PRIVATE_THREADS = 1 << 36
    USE_EXTERNAL_STICKERS = 1 << 37

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
    )

    # Special members
    NONE = 0
    ALL = AntiFlag()


class ChannelTypes(IntEnum):
    """Types of channel"""

    GUILD_TEXT = 0
    DM = 1
    GUILD_VOICE = 2
    GROUP_DM = 3
    GUILD_CATEGORY = 4
    GUILD_NEWS = 5
    GUILD_STORE = 6
    GUILD_NEWS_THREAD = 10
    GUILD_PUBLIC_THREAD = 11
    GUILD_PRIVATE_THREAD = 12
    GUILD_STAGE_VOICE = 13

    @property
    def guild(self) -> bool:
        return self.value not in {1, 3}

    @property
    def voice(self) -> bool:
        return self.value in {2, 13}


class ComponentTypes(IntEnum):
    """
    The types of components supported by discord
    """

    ACTION_ROW = 1
    BUTTON = 2
    SELECT = 3


class CommandTypes(IntEnum):
    """
    The interaction commands supported by discord
    """

    CHAT_INPUT = 1
    USER = 2
    MESSAGE = 3


class InteractionTypes(IntEnum):
    """
    The type of interaction received by discord
    """

    PING = 1
    APPLICATION_COMMAND = 2
    MESSAGE_COMPONENT = 3
    AUTOCOMPLETE = 4


class ButtonStyles(IntEnum):
    """
    The styles of buttons supported
    """

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
    """Types of mention"""

    EVERYONE = "everyone"
    ROLES = "roles"
    USERS = "users"


class OverwriteTypes(IntEnum):
    """Types of permission overwrite"""

    ROLE = 0
    MEMBER = 1


class DefaultNotificationLevels(IntEnum):
    """Default Notification levels for dms and guilds"""

    ALL_MESSAGES = 0
    ONLY_MENTIONS = 1


class ExplicitContentFilterLevels(IntEnum):
    """Automatic filtering of explicit content"""

    DISABLED = 0
    MEMBERS_WITHOUT_ROLES = 1
    ALL_MEMBERS = 2


class MFALevels(IntEnum):
    """Does the user use 2FA"""

    NONE = 0
    ELEVATED = 1


class VerificationLevels(IntEnum):
    """Levels of verification needed by a guild"""

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
    """A guilds NSFW Level"""

    DEFAULT = 0
    EXPLICIT = 1
    SAFE = 2
    AGE_RESTRICTED = 3


class PremiumTiers(IntEnum):
    """The boost level of a server"""

    NONE = 0
    TIER_1 = 1
    TIER_2 = 2
    TIER_3 = 3


class SystemChannelFlags(DiscordIntFlag):
    """System channel settings"""

    SUPPRESS_JOIN_NOTIFICATIONS = 1 << 0
    SUPPRESS_PREMIUM_SUBSCRIPTIONS = 1 << 1
    SUPPRESS_GUILD_REMINDER_NOTIFICATIONS = 1 << 2

    # Special members
    NONE = 0
    ALL = AntiFlag()


class VideoQualityModes(IntEnum):
    """Video quality settings"""

    AUTO = 1
    FULL = 2


class AutoArchiveDuration(IntEnum):
    """Thread archive duration, in minutes"""

    ONE_HOUR = 60
    ONE_DAY = 1440
    THREE_DAY = 4320
    ONE_WEEK = 10080


class ActivityType(IntEnum):
    """The types of presence activity that can be used in presences

    !!! note
        Only `GAME` `STREAMING` `LISTENING` `WATCHING` and `COMPETING` are usable by bots
    """

    GAME = 0  # "Playing Rocket League"
    STREAMING = 1  # "Streaming Rocket League"
    LISTENING = 2  # "Listening to Spotify"
    WATCHING = 3  # "Watching YouTube Together"
    CUSTOM = 4  # ":smiley: I am cool"
    COMPETING = 5  # "Competing in Arena World Champions"

    PLAYING = GAME


class Status(str, Enum):
    """Represents the statuses a user may have"""

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
