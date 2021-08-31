import asyncio
from typing import Callable, Coroutine, Any

import attr


@attr.s(slots=True, kw_only=True, on_setattr=[attr.setters.convert, attr.setters.validate])
class BaseCommand:
    skin: Any = attr.ib(default=None)
    enabled: bool = attr.ib(default=True)

    checks: list = attr.ib(factory=list)

    callback: Callable[..., Coroutine] = attr.ib(default=None)
    error_callback: Callable[..., Coroutine] = attr.ib(default=None)
    pre_run_callback: Callable[..., Coroutine] = attr.ib(default=None)
    post_run_callback: Callable[..., Coroutine] = attr.ib(default=None)

    def __setattr__(self, key, value):
        """Intercept the callback attribute being set, and grab checks from the object"""
        # todo: This but for interaction context... so we dont need to do ugliness in client.py
        if key == "callback":
            # todo: grab checks from object
            pass
        super().__setattr__(key, value)

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
