import asyncio
from typing import Callable, Coroutine, Any

import attr

from dis_snek.mixins.serialization import DictSerializationMixin
from dis_snek.utils.serializer import no_export_meta


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

    scale: Any = attr.ib(default=None, metadata=no_export_meta)
    """The scale this command belongs to"""
    enabled: bool = attr.ib(default=True, metadata=no_export_meta)
    """Whether this can be run at all"""

    checks: list = attr.ib(factory=list)
    """Any checks that must be *checked* before the command can run"""

    callback: Callable[..., Coroutine] = attr.ib(default=None, metadata=no_export_meta)
    """The coroutine to be called for this command"""
    error_callback: Callable[..., Coroutine] = attr.ib(default=None, metadata=no_export_meta)
    """The coroutine to be called when an error occurs"""
    pre_run_callback: Callable[..., Coroutine] = attr.ib(default=None, metadata=no_export_meta)
    """The coroutine to be called before the command is executed, **but** after the checks"""
    post_run_callback: Callable[..., Coroutine] = attr.ib(default=None, metadata=no_export_meta)
    """The coroutine to be called after the command has executed"""

    def __attrs_post_init__(self):
        if self.callback is not None:
            if hasattr(self.callback, "checks"):
                self.checks += self.callback.checks

    async def _call_callback(self, callback_object, *args, **kwargs):
        if self.scale is not None:
            return await callback_object(self.scale, *args, **kwargs)
        else:
            return await callback_object(*args, **kwargs)

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
                    await self._call_callback(self.pre_run_callback, context, *args, **kwargs)

                await self._call_callback(self.callback, context, *args, **kwargs)

                if self.post_run_callback is not None:
                    await self._call_callback(self.post_run_callback, context, *args, **kwargs)

        except Exception as e:
            if self.error_callback:
                await self._call_callback(self.error_callback, e, context, *args, **kwargs)
            else:
                raise

    async def _can_run(self, context):
        """
        Determines if this command can be run.

        parameters:
            context: The context of the command
        """
        if not self.enabled:
            return False

        for _c in self.checks:
            if not await _c(context):
                return False

        if self.scale and self.scale.scale_checks:
            for _c in self.scale.scale_checks:
                if not await _c(context):
                    return False

        return True

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

    name: str = attr.ib()
    """The name of the command."""


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
