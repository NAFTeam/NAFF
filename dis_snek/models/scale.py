import asyncio
import inspect
import logging
from typing import List, TYPE_CHECKING, Callable, Coroutine

from dis_snek.const import logger_name, MISSING
from dis_snek.models.application_commands import InteractionCommand, ComponentCommand
from dis_snek.models.auto_defer import AutoDefer
from dis_snek.models.command import MessageCommand, BaseCommand
from dis_snek.models.listener import Listener
from dis_snek.tasks import Task
from dis_snek.utils.misc_utils import wrap_partial

if TYPE_CHECKING:
    from dis_snek.client import Snake

log = logging.getLogger(logger_name)


class Scale:
    """
    A class that allows you to separate your commands and listeners into separate files.
    Skins require an entrypoint in the same file called `setup`, this function allows
    client to load the Scale.

    ??? Hint "Example Usage:"
        ```python
        class ExampleScale(Scale):
            def __init__(self, bot):
                print("Scale Created")

            @message_command
            async def some_command(self, context):
                await ctx.send(f"I was sent from a scale called {self.name}")
        ```

    parameters:
        bot Snake: A reference to the client

    Attributes:
        bot Snake: A reference to the client
        name str: The name of this Scale (`read-only`)
        description str: A description of this Scale
        scale_checks str: A list of checks to be ran on any command in this scale
        scale_prerun List: A list of coroutines to be run before any command in this scale
        scale_postrun List: A list of coroutines to be run after any command in this scale
    """

    bot: "Snake"
    __name: str
    extension_name: str
    description: str
    scale_checks: List
    scale_prerun: List
    scale_postrun: List
    listeners: List
    _commands: List
    auto_defer: AutoDefer

    def __new__(cls, bot: "Snake", *args, **kwargs):
        new_cls = super().__new__(cls)
        new_cls.bot = bot
        new_cls.__name = cls.__name__
        new_cls.scale_checks = []
        new_cls.scale_prerun = []
        new_cls.scale_postrun = []
        new_cls.auto_defer = MISSING

        new_cls.description = kwargs.get("Description", None)
        if not new_cls.description:
            new_cls.description = inspect.cleandoc(cls.__doc__) if cls.__doc__ else None

        # load commands from class
        new_cls._commands = []
        new_cls._listeners = []

        for name, val in inspect.getmembers(new_cls, predicate=lambda x: isinstance(x, (BaseCommand, Listener, Task))):
            if isinstance(val, BaseCommand):
                val.scale = new_cls
                val = wrap_partial(val, new_cls)

                new_cls._commands.append(val)

                if isinstance(val, ComponentCommand):
                    bot.add_component_callback(val)
                elif isinstance(val, InteractionCommand):
                    bot.add_interaction(val)
                else:
                    bot.add_message_command(val)
            elif isinstance(val, Listener):
                val = wrap_partial(val, new_cls)
                bot.add_listener(val)
                new_cls.listeners.append(val)
            elif isinstance(val, Task):
                wrap_partial(val, new_cls)

        log.debug(
            f"{len(new_cls._commands)} commands and {len(new_cls.listeners)} listeners"
            f" have been loaded from `{new_cls.name}`"
        )

        new_cls.extension_name = inspect.getmodule(new_cls).__name__
        new_cls.bot.scales[new_cls.name] = new_cls
        return new_cls

    @property
    def __name__(self):
        return self.name

    @property
    def commands(self):
        """Get the commands from this Scale"""
        return self._commands

    @property
    def listeners(self):
        """Get the listeners from this Scale"""
        return self._listeners

    @property
    def name(self):
        return self.__name

    def shed(self):
        """
        Called when this Scale is being removed.
        """
        for func in self._commands:
            if isinstance(func, ComponentCommand):
                for listener in func.listeners:
                    self.bot._component_callbacks.pop(listener)
            elif isinstance(func, InteractionCommand):
                for scope in func.scopes:
                    if self.bot.interactions.get(scope):
                        self.bot.interactions[scope].pop(func.resolved_name, [])
            elif isinstance(func, MessageCommand):
                if self.bot.commands[func.name]:
                    self.bot.commands.pop(func.name)
        for func in self.listeners:
            self.bot.listeners[func.event].remove(func)

        self.bot.scales.pop(self.name, None)
        log.debug(f"{self.name} has been shed")

    def add_scale_auto_defer(self, ephemeral: bool = False, time_until_defer: float = 0.0):
        """
        Add a auto defer for all commands in this scale

        Args:
            ephemeral: Should the command be deferred as ephemeral
            time_until_defer: How long to wait before deferring automatically
        """
        self.auto_defer = AutoDefer(enabled=True, ephemeral=ephemeral, time_until_defer=time_until_defer)

    def add_scale_check(self, coroutine: Callable[..., Coroutine]) -> None:
        """
        Add a coroutine as a check for all commands in this scale to run. This coroutine must take **only** the parameter `context`.

        ??? Hint "Example Usage:"
            ```python
            def __init__(self, bot):
                self.bot = bot
                self.add_scale_check(self.example)

            @staticmethod
            async def example(context: Context):
                if context.author.id == 123456789:
                    return True
                return False
            ```
        Args:
            coroutine: The coroutine to use as a check
        """
        if not asyncio.iscoroutinefunction(coroutine):
            raise TypeError("Check must be a coroutine")

        if not self.scale_checks:
            self.scale_checks = []

        self.scale_checks.append(coroutine)

    def add_scale_prerun(self, coroutine: Callable[..., Coroutine]):
        """
        Add a coroutine to be run **before** all commands in this Scale.

        Note:
            Pre-runs will **only** be run if the commands checks pass

        ??? Hint "Example Usage:"
            ```python
            def __init__(self, bot):
                self.bot = bot
                self.add_scale_prerun(self.example)

            async def example(self, context: Context):
                await ctx.send("I ran first")
            ```

        Args:
            coroutine: The coroutine to run
        """
        if not asyncio.iscoroutinefunction(coroutine):
            raise TypeError("Callback must be a coroutine")

        if not self.scale_prerun:
            self.scale_prerun = []
        self.scale_prerun.append(coroutine)

    def add_scale_postrun(self, coroutine: Callable[..., Coroutine]):
        """
        Add a coroutine to be run **after** all commands in this Scale.

        ??? Hint "Example Usage:"
            ```python
            def __init__(self, bot):
                self.bot = bot
                self.add_scale_postrun(self.example)

            async def example(self, context: Context):
                await ctx.send("I ran first")
            ```

        Args:
            coroutine: The coroutine to run
        """
        if not asyncio.iscoroutinefunction(coroutine):
            raise TypeError("Callback must be a coroutine")

        if not self.scale_postrun:
            self.scale_postrun = []
        self.scale_postrun.append(coroutine)
