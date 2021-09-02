import inspect
import logging
from typing import List

from dis_snek.const import logger_name
from dis_snek.models.command import BaseCommand

log = logging.getLogger(logger_name)


class Skin:
    _commands: List
    description: str

    def __new__(cls, bot: "Snake", *args, **kwargs):
        cls.description = kwargs.get("Description", None)
        if not cls.description:
            cls.description = inspect.cleandoc(cls.__doc__) if cls.__doc__ else None

        # load commands from class
        cls._commands = []

        for name, val in cls.__dict__.items():
            if isinstance(val, BaseCommand):
                val.skin = cls
                cls._commands.append(val)
                bot.add_interaction(val)

        log.debug(f"{len(cls._commands)} application commands have been loaded from `{cls.__name__}`")

    def __init__(self, bot):
        # forces a user to have some sort of bot attribute
        self.bot = bot

    @property
    def commands(self):
        return self._commands
