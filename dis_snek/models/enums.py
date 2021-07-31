import logging
from enum import _decompose
from enum import EnumMeta
from enum import IntEnum
from enum import IntFlag
from functools import reduce
from operator import or_

from dis_snek.const import logger_name

log = logging.getLogger(logger_name)


class AntiFlag:
    def __init__(self, anti=0):
        self.anti = anti

    def __get__(self, instance, cls):
        negative = ~cls(self.anti)
        positive = cls(reduce(or_, negative))
        return positive


def _distinct(source):
    return (x for x in source if (x.value & (x.value - 1)) == 0 and x.value != 0)


class DistinctFlag(EnumMeta):
    def __iter__(cls):
        yield from _distinct(super().__iter__())


class DistinctMixin:
    def __iter__(self):
        yield from _decompose(self.__class__, self)[0]


class WebSocketOPCodes(IntEnum):
    DISPATCH = 0
    HEARTBEAT = 1
    IDENTIFY = 2
    PRESENCE = 3
    VOICE_STATE = 4
    VOICE_PING = 5
    RESUME = 6
    RECONNECT = 7
    REQUEST_MEMBERS = 8
    INVALIDATE_SESSION = 9
    HELLO = 10
    HEARTBEAT_ACK = 11
    GUILD_SYNC = 12


class Intents(DistinctMixin, IntFlag, metaclass=DistinctFlag):
    # Intents defined by Discord API
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
        GUILDS=False,
        GUILD_MEMBERS=False,
        GUILD_BANS=False,
        GUILD_EMOJIS_AND_STICKERS=False,
        GUILD_INTEGRATIONS=False,
        GUILD_WEBHOOKS=False,
        GUILD_INVITES=False,
        GUILD_VOICE_STATES=False,
        GUILD_PRESENCES=False,
        GUILD_MESSAGES=False,
        GUILD_MESSAGE_REACTIONS=False,
        GUILD_MESSAGE_TYPING=False,
        DIRECT_MESSAGES=False,
        DIRECT_MESSAGE_REACTIONS=False,
        DIRECT_MESSAGE_TYPING=False,
        MESSAGES=False,
        REACTIONS=False,
        TYPING=False,
        PRIVILEGED=False,
        NON_PRIVILEGED=False,
        DEFAULT=True,
        ALL=False,
    ):
        """
        Set your desired intents
        """
        kwargs = locals()
        del kwargs["cls"]

        base = cls.NONE
        for key in kwargs:
            if kwargs[key]:
                base = base | getattr(cls, key)
        return base


class UserFlags(DistinctMixin, IntFlag, metaclass=DistinctFlag):
    # Flags defined by Discord API
    DISCORD_EMPLOYEE = 1 << 0
    PARTNERED_SERVER_OWNER = 1 << 1
    HYPESQUAD_EVENTS = 1 << 2
    BUG_HUNTER_LEVEL_1 = 1 << 3

    HOUSE_BRAVERY = 1 << 6
    HOUSE_BRILLIANCE = 1 << 7
    HOUSE_BALANCE = 1 << 8
    EARLY_SUPPORTER = 1 << 9
    TEAM_USER = 1 << 10

    BUG_HUNTER_LEVEL_2 = 1 << 14

    VERIFIED_BOT = 1 << 16
    EARLY_VERIFIED_BOT_DEVELOPER = 1 << 17
    DISCORD_CERTIFIED_MODERATOR = 1 << 18

    # Shortcuts/grouping/aliases
    HYPESQUAD = HOUSE_BRAVERY | HOUSE_BRILLIANCE | HOUSE_BALANCE
    BUG_HUNTER = BUG_HUNTER_LEVEL_1 | BUG_HUNTER_LEVEL_2

    # Special members
    NONE = 0
    ALL = AntiFlag()


class PremiumTypes(IntEnum):
    NONE = 0
    NITRO_CLASSIC = 1
    NITRO = 2


class MessageTypes(IntEnum):
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


class MessageActivityTypes(IntEnum):
    JOIN = 1
    SPECTATE = 2
    LISTEN = 3
    JOIN_REQUEST = 5


class MessageFlags(DistinctMixin, IntFlag, metaclass=DistinctFlag):
    # Flags defined by Discord API
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


class ChannelTypes(IntEnum):
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


class ComponentType(IntEnum):
    """
    The types of components supported by discord
    """

    ACTION_ROW = 1
    BUTTON = 2
    SELECT = 3


class ButtonStyle(IntEnum):
    """
    The styles of buttons supported
    """

    BLUE = 1
    BLURPLE = 1
    GRAY = 2
    GREY = 2
    GREEN = 3
    RED = 4
    URL = 5

    PRIMARY = 1
    SECONDARY = 2
    SUCCESS = 3
    DANGER = 4
