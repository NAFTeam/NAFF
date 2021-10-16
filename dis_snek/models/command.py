import asyncio
import logging
from typing import Callable, Coroutine, Any

import attr

from dis_snek.const import MISSING, logger_name
from dis_snek.errors import CommandOnCooldown, CommandCheckFailure, MaxConcurrencyReached
from dis_snek.mixins.serialization import DictSerializationMixin
from dis_snek.models.cooldowns import Cooldown, Buckets, MaxConcurrency
from dis_snek.utils.attr_utils import docs
from dis_snek.utils.serializer import no_export_meta

log = logging.getLogger(logger_name)


@attr.s(slots=True, kw_only=True, on_setattr=[attr.setters.convert, attr.setters.validate])
class BaseCommand(DictSerializationMixin):
    """
    An object all commands inherit from.
    Outlines the basic structure of a command, and handles checks.

    attributes:
        scale: The scale this command belongs to.
        enabled: Whether this command is enabled
        checks: Any checks that must be run before this command can be run
        callback: The coroutine to be called for this command
        error_callback: The coroutine to be called when an error occurs
        pre_run_callback: A coroutine to be called before this command is run **but** after the checks
        post_run_callback: A coroutine to be called after this command has run

    """

    scale: Any = attr.ib(default=None, metadata=docs("The scale this command belongs to") | no_export_meta)

    enabled: bool = attr.ib(default=True, metadata=docs("Whether this can be run at all") | no_export_meta)
    checks: list = attr.ib(factory=list, metadata=docs("Any checks that must be *checked* before the command can run"))
    cooldown: Cooldown = attr.ib(default=MISSING, metadata=docs("An optional cooldown to apply to the command"))
    max_concurrency: MaxConcurrency = attr.ib(
        default=MISSING, metadata=docs("An optional maximum number of concurrent instances to apply to the command")
    )

    callback: Callable[..., Coroutine] = attr.ib(
        default=None, metadata=docs("The coroutine to be called for this command") | no_export_meta
    )
    error_callback: Callable[..., Coroutine] = attr.ib(
        default=None, metadata=no_export_meta | docs("The coroutine to be called when an error occurs")
    )
    pre_run_callback: Callable[..., Coroutine] = attr.ib(
        default=None,
        metadata=no_export_meta
        | docs("The coroutine to be called before the command is executed, **but** after the checks"),
    )
    post_run_callback: Callable[..., Coroutine] = attr.ib(
        default=None, metadata=no_export_meta | docs("The coroutine to be called after the command has executed")
    )

    def __attrs_post_init__(self):
        if self.callback is not None:
            if hasattr(self.callback, "checks"):
                self.checks += self.callback.checks
            if hasattr(self.callback, "cooldown"):
                self.cooldown = self.callback.cooldown
            if hasattr(self.callback, "max_concurrency"):
                self.max_concurrency = self.callback.max_concurrency

    async def __call__(self, context, *args, **kwargs):
        """
        Calls this command.

        parameters:
            context: The context of this command
            args: Any
            kwargs: Any
        """
        try:
            if await self._can_run(context):
                if self.pre_run_callback is not None:
                    await self.pre_run_callback(context, *args, **kwargs)

                if self.scale is not None and self.scale.scale_prerun:
                    await self.scale.scale_prerun(context, *args, **kwargs)

                await self.callback(context, *args, **kwargs)

                if self.post_run_callback is not None:
                    await self.post_run_callback(context, *args, **kwargs)

                if self.scale is not None and self.scale.scale_postrun:
                    await self.scale.scale_postrun(context, *args, **kwargs)

        except Exception as e:
            if self.error_callback:
                await self.error_callback(e, context, *args, **kwargs)
            else:
                raise
        finally:
            if self.max_concurrency is not MISSING:
                await self.max_concurrency.release(context)

    async def _can_run(self, context):
        """
        Determines if this command can be run.

        parameters:
            context: The context of the command
        """
        max_conc_acquired = False  # signals if a semaphore has been acquired, for exception handling

        try:
            if not self.enabled:
                return False

            for _c in self.checks:
                if not await _c(context):
                    raise CommandCheckFailure(self, _c)

            if self.scale and self.scale.scale_checks:
                for _c in self.scale.scale_checks:
                    if not await _c(context):
                        raise CommandCheckFailure(self, _c)

            if self.max_concurrency is not MISSING:
                if not await self.max_concurrency.acquire(context):
                    raise MaxConcurrencyReached(self, self.max_concurrency)

            if self.cooldown is not MISSING:
                if not await self.cooldown.acquire_token(context):
                    raise CommandOnCooldown(self, await self.cooldown.get_cooldown(context))

            return True

        except Exception:
            if max_conc_acquired:
                await self.max_concurrency.release(context)
            raise

    def error(self, call: Callable[..., Coroutine]):
        """A decorator to declare a coroutine as one that will be run upon an error."""
        if not asyncio.iscoroutinefunction(call):
            raise TypeError("Error handler must be coroutine")
        self.error_callback = call
        return call

    def pre_run(self, call: Callable[..., Coroutine]):
        """A decorator to declare a coroutine as one that will be run before the command"""
        if not asyncio.iscoroutinefunction(call):
            raise TypeError("pre_run must be coroutine")
        self.pre_run_callback = call
        return call

    def post_run(self, call: Callable[..., Coroutine]):
        """A decorator to declare a coroutine as one that will be run after the command has"""
        if not asyncio.iscoroutinefunction(call):
            raise TypeError("post_run must be coroutine")
        self.post_run_callback = call
        return call


@attr.s(slots=True, kw_only=True, on_setattr=[attr.setters.convert, attr.setters.validate])
class MessageCommand(BaseCommand):
    """
    Represents a command triggered by standard message.
    """

    name: str = attr.ib(metadata=docs("The name of the command"))


def message_command(
    name: str = None,
):
    """
    A decorator to declare a coroutine as a message command.

    parameters:
        name: The name of the command, defaults to the name of the coroutine
    returns:
        Message Command Object
    """

    def wrapper(func):
        if not asyncio.iscoroutinefunction(func):
            raise ValueError("Commands must be coroutines")
        cmd = MessageCommand(name=name or func.__name__, callback=func)
        return cmd

    return wrapper


def check(check: Callable[..., Coroutine]):
    """
    Add a check to a command.

    parameters:
        check: A coroutine as a check for this command
    """

    def wrapper(coro):
        if isinstance(coro, BaseCommand):
            coro.checks.append(check)
            return
        if not hasattr(coro, "checks"):
            coro.checks = []
        coro.checks.append(check)
        return coro

    return wrapper


def cooldown(bucket: Buckets, rate: int, interval: float):
    """
    Add a cooldown to a command

    Args:
        bucket: The bucket used to track cooldowns
        rate: How many commands may be ran per interval
        interval: How many seconds to wait for a cooldown
    """

    def wrapper(coro: Callable[..., Coroutine]):
        cooldown_obj = Cooldown(bucket, rate, interval)

        coro.cooldown = cooldown_obj

        return coro

    return wrapper


def max_concurrency(bucket: Buckets, concurrent: int):
    """
    Add a maximum number of concurrent instances to the command.

    Args:
        bucket: The bucket to enforce the maximum within
        concurrent: The maximum number of concurrent instances to allow
    """

    def wrapper(coro: Callable[..., Coroutine]):
        max_conc = MaxConcurrency(concurrent, bucket)

        coro.max_concurrency = max_conc

        return coro

    return wrapper
