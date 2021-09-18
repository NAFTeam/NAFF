import asyncio
import inspect
import logging
from typing import List, TYPE_CHECKING, Callable, Coroutine

from dis_snek.const import logger_name
from dis_snek.models.command import MessageCommand
from dis_snek.models.application_commands import InteractionCommand

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
        bot: A reference to the client

    Attributes:
        bot Snake: A reference to the client
        name str: The name of this Scale
        description str: A description of this Scale
        scale_checks str: A list of checks to be ran on any command in this scale
        scale_prerun List: A list of coroutines to be run before any command in this scale
        scale_postrun List: A list of coroutines to be run after any command in this scale
    """

    bot: "Snake"
    _commands: List
    name: str
    description: str
    scale_checks: List
    scale_prerun: List
    scale_postrun: List

    def __new__(cls, bot: "Snake", *args, **kwargs):
        cls.bot = bot
        cls.name = cls.__name__
        cls.bot.scales[cls.name] = cls
        cls.scale_checks = []

        cls.description = kwargs.get("Description", None)
        if not cls.description:
            cls.description = inspect.cleandoc(cls.__doc__) if cls.__doc__ else None

        # load commands from class
        cls._commands = []

        new_cls = super().__new__(cls)

        for name, val in cls.__dict__.items():
            if isinstance(val, InteractionCommand):
                val.scale = new_cls
                new_cls._commands.append(val)
                bot.add_interaction(val)
            if isinstance(val, MessageCommand):
                val.scale = new_cls
                new_cls._commands.append(val)
                bot.add_message_command(val)

        log.debug(f"{len(new_cls._commands)} application commands have been loaded from `{new_cls.name}`")

        return new_cls

    @property
    def commands(self):
        """Get the commands from this Scale"""
        return self._commands

    def shed(self):
        """
        Called when this Scale is being removed.
        """
        for cmd in self._commands:
            if isinstance(cmd, InteractionCommand):
                if self.bot.interactions.get(cmd.scope) and self.bot.interactions[cmd.scope].get(cmd.name):
                    self.bot.interactions[cmd.scope].pop(cmd.name)
            if isinstance(cmd, MessageCommand):
                if self.bot.commands[cmd.name]:
                    self.bot.commands.pop(cmd.name)

        self.bot.scales.pop(self.__name__)
        log.debug(f"{self.__name__} has been shed")

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

        Args:
            coroutine: The coroutine to run
        """
        if not asyncio.iscoroutinefunction(coroutine):
            raise TypeError("Callback must be a coroutine")

        if not self.scale_postrun:
            self.scale_postrun = []
        self.scale_postrun.append(coroutine)
