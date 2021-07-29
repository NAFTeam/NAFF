from enum import IntEnum, IntFlag, EnumMeta, _decompose
from operator import or_
from functools import reduce


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

    # Special members
    none = 0
    all = AntiFlag()


# print(int(Intents.all))
for e in Intents:
    print(e)

for i in Intents.PRIVILEGED:
    print(i)


print(int(Intents.all))
print(Intents.MESSAGES)
