import inspect
import logging
from typing import List

from dis_snek.const import logger_name
from dis_snek.models.command import BaseCommand, MessageCommand
from dis_snek.models.discord_objects.interactions import InteractionCommand

log = logging.getLogger(logger_name)


class Scale:
    """
    A class that allows you to separate your commands and listeners into separate files.
    Skins require an entrypoint in the same file called `setup`, this function allows
    client to load the Scale.

    :param bot: A reference to the client
    """

    _commands: List
    description: str

    def __new__(cls, bot: "Snake", *args, **kwargs):
        cls.bot = bot
        cls.description = kwargs.get("Description", None)
        if not cls.description:
            cls.description = inspect.cleandoc(cls.__doc__) if cls.__doc__ else None

        # load commands from class
        cls._commands = []

        for name, val in cls.__dict__.items():
            if isinstance(val, InteractionCommand):
                val.skin = cls
                cls._commands.append(val)
                bot.add_interaction(val)
            if isinstance(val, MessageCommand):
                val.skin = cls
                cls._commands.append(val)
                bot.add_message_command(val)

        log.debug(f"{len(cls._commands)} application commands have been loaded from `{cls.__name__}`")

    @property
    def commands(self):
        return self._commands
