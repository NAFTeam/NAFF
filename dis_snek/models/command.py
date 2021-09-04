import asyncio
from typing import Callable, Coroutine, Any

import attr

from dis_snek.mixins.serialization import DictSerializationMixin
from dis_snek.utils.serializer import no_export_meta


@attr.s(slots=True, kw_only=True, on_setattr=[attr.setters.convert, attr.setters.validate])
class BaseCommand(DictSerializationMixin):
    skin: Any = attr.ib(default=None, metadata=no_export_meta)
    enabled: bool = attr.ib(default=True, metadata=no_export_meta)

    checks: list = attr.ib(factory=list)

    callback: Callable[..., Coroutine] = attr.ib(default=None, metadata=no_export_meta)
    error_callback: Callable[..., Coroutine] = attr.ib(default=None, metadata=no_export_meta)
    pre_run_callback: Callable[..., Coroutine] = attr.ib(default=None, metadata=no_export_meta)
    post_run_callback: Callable[..., Coroutine] = attr.ib(default=None, metadata=no_export_meta)

    def __attrs_post_init__(self):
        if self.callback is not None:
            # todo load checks here
            pass

    async def _call_callback(self, callback_object, *args, **kwargs):
        if self.skin is not None:
            return await callback_object(self.skin, *args, **kwargs)
        else:
            return await callback_object(*args, **kwargs)

    async def __call__(self, context, *args, **kwargs):
        """
        Calls this command.

        :param context: The context of this command.
        :param args:
        :param kwargs:
        :return:
        """
        try:
            if await self.can_run(context):
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

    async def can_run(self, context):
        """
        Determines if this command can be run.

        :param context:
        :return: boolean if this command can be run.
        """
        # todo checks.
        if not self.enabled:
            return False
        return True

    def error(self, call: Callable[..., Coroutine]):
        if not asyncio.iscoroutinefunction(call):
            raise TypeError("Error handler must be coroutine")
        self.error_callback = call
        return call

    def pre_run(self, call: Callable[..., Coroutine]):
        if not asyncio.iscoroutinefunction(call):
            raise TypeError("pre_run must be coroutine")
        self.pre_run_callback = call
        return call

    def post_run(self, call: Callable[..., Coroutine]):
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


def message_command(
    name: str = None,
):
    """
    A decorator to declare a coroutine as a message command.

    :param name: The name of the command, defaults to the name of the coroutine
    :return: MessageCommand Object
    """

    def wrapper(func):
        if not asyncio.iscoroutinefunction(func):
            raise ValueError("Commands must be coroutines")
        cmd = MessageCommand(name=name or func.__name__, callback=func)
        return cmd

    return wrapper
