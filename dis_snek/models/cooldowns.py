import time
from enum import Enum, IntEnum
from typing import TYPE_CHECKING

from dis_snek.const import MISSING

if TYPE_CHECKING:
    from dis_snek.models.discord_objects.context import Context


class Buckets(IntEnum):
    """
    Outlines the cooldown buckets that may be used.
    Should a bucket for guilds exist, and the command is invoked in a DM, a sane default will be used.

    ??? note
        To add your own, override this
    """

    DEFAULT = 0
    """Default is the same as user"""
    USER = 1
    """Per user cooldowns"""
    GUILD = 2
    """Per guild cooldowns"""
    CHANNEL = 3
    """Per channel cooldowns"""
    MEMBER = 4
    """Per guild member cooldowns"""
    CATEGORY = 5
    """Per category cooldowns"""
    ROLE = 6
    """Per role cooldowns"""

    async def get_key(self, context: "Context"):
        if self is Buckets.USER:
            return context.author.id
        elif self is Buckets.GUILD:
            return context.guild.id if context.guild else context.author.id
        elif self is Buckets.CHANNEL:
            return context.channel.id
        elif self is Buckets.MEMBER:
            return (context.guild.id, context.author.id) if context.guild else context.author.id
        elif self is Buckets.CATEGORY:
            return await context.channel.parent.id if context.channel.parent else context.channel.id
        elif self is Buckets.ROLE:
            return context.channel.id if not context.guild else await context.author.top_role.id
        else:
            return context.author.id

    def __call__(self, context: "Context"):
        return self.get_key(context)


class Cooldown:
    """
    Manages cooldowns and their respective buckets for a command
    """

    __slots__ = "bucket", "cooldown_repositories", "rate", "interval"

    def __init__(self, cooldown_bucket: Buckets, rate: int, interval: float):
        self.bucket: Buckets = cooldown_bucket
        self.cooldown_repositories = {}
        self.rate: int = rate
        self.interval: float = interval

    async def _get_cooldown(self, context: "Context") -> "CooldownSystem":
        key = await self.bucket(context)

        if key not in self.cooldown_repositories:
            cooldown = CooldownSystem(self.rate, self.interval)
            self.cooldown_repositories[key] = cooldown
            return cooldown
        return self.cooldown_repositories.get(await self.bucket(context))

    async def acquire_token(self, context: "Context") -> bool:
        """
        Attempt to acquire a token for a command to run.
        Uses the context of the command to use the correct CooldownSystem

        Args:
            context: The context of the command

        Returns:
            True if a token was acquired, False if not
        """
        cooldown = await self._get_cooldown(context)

        return cooldown.acquire_token()

    async def get_cooldown_time(self, context: "Context") -> float:
        """
        Get the remaining cooldown time.

        Args:
            context: The context of the command

        Returns:
            remaining cooldown time, will return 0 if the cooldown has not been reached
        """
        cooldown = await self._get_cooldown(context)
        return cooldown.get_cooldown_time()

    async def on_cooldown(self, context: "Context") -> bool:
        """
        Returns the cooldown state of the command

        Args:
            context: The context of the command

        Returns:
            boolean state if the command is on cooldown or not
        """
        cooldown = await self._get_cooldown(context)
        return cooldown.on_cooldown()

    async def reset_all(self) -> None:
        """
        Resets this cooldown system to its initial state.

        !!! warning:
            To be clear, this will reset **all** cooldowns for this command to their initial states
        """
        # this doesnt need to be async, but for consistency, it is
        self.cooldown_repositories = {}

    async def reset(self, context: "Context") -> None:
        """
        Resets the cooldown for the bucket of which invoked this command

        Args:
            context: The context of the command
        """
        cooldown = await self._get_cooldown(context)
        cooldown.reset()


class CooldownSystem:
    """
    Represents a cooldown system for commands

    Attributes:
        rate: How many commands may be ran per interval
        interval: How many seconds to wait for a cooldown
        opened: When this cooldown session began
    """

    __slots__ = "rate", "interval", "opened", "_tokens"

    def __init__(self, rate: int, interval: float):
        self.rate: int = rate
        self.interval: float = interval
        self.opened: float = 0.0

        self._tokens: int = self.rate

        # sanity checks
        if self.rate < 1:
            raise ValueError("Cooldown rate must be greater than 0")
        if self.interval < 1:
            raise ValueError("Cooldown interval must be greater than 0")

    def reset(self) -> None:
        """
        Resets the tokens for this cooldown
        """
        self._tokens = self.rate
        self.opened = 0.0

    def on_cooldown(self) -> bool:
        """
        Returns the cooldown state of the command
        Returns:
            boolean state if the command is on cooldown or not
        """
        self.determine_cooldown()

        if self._tokens == 0:
            return False
        return True

    def acquire_token(self) -> bool:
        """
        Attempt to acquire a token for a command to run.

        Returns:
            True if a token was acquired, False if not
        """
        self.determine_cooldown()

        if self._tokens == 0:
            return False
        self._tokens -= 1
        self.opened = time.time()

        return True

    def get_cooldown_time(self) -> float:
        """
        Returns how long until the cooldown will reset.
        Returns:
            remaining cooldown time, will return 0 if the cooldown has not been reached
        """
        if self._tokens != 0:
            return 0
        return self.interval - (time.time() - self.opened)

    def determine_cooldown(self) -> None:
        """
        Determines the state of the cooldown system
        """
        c_time = time.time()

        if c_time > self.opened + self.interval:
            # cooldown has expired, reset the cooldown
            self.reset()
