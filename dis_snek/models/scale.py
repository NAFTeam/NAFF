import inspect
import logging
from typing import List, TYPE_CHECKING

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

    parameters:
        bot: A reference to the client
    """

    bot: "Snake"
    _commands: List
    description: str

    def __new__(cls, bot: "Snake", *args, **kwargs):
        cls.bot = bot
        cls.bot.scales[cls.__name__] = cls

        cls.description = kwargs.get("Description", None)
        if not cls.description:
            cls.description = inspect.cleandoc(cls.__doc__) if cls.__doc__ else None

        # load commands from class
        cls._commands = []

        for name, val in cls.__dict__.items():
            if isinstance(val, InteractionCommand):
                val.scale = cls
                cls._commands.append(val)
                bot.add_interaction(val)
            if isinstance(val, MessageCommand):
                val.scale = cls
                cls._commands.append(val)
                bot.add_message_command(val)

        log.debug(f"{len(cls._commands)} application commands have been loaded from `{cls.__name__}`")
        return cls

    def __del__(self):
        self.shed()

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

    @property
    def commands(self):
        return self._commands
