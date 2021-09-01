import inspect
from typing import List

from dis_snek.models.command import BaseCommand
from dis_snek.models.discord_objects.interactions import SlashCommand, slash_command


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

        # attempt to load commands into bot
        for cmd in cls._commands:
            if cmd.scope not in bot.interactions:
                bot.interactions[cmd.scope] = {}
            bot.interactions[cmd.scope][cmd.name] = cmd

    def __init__(self, bot):
        # forces a user to have some sort of bot attribute
        self.bot = bot

    @property
    def commands(self):
        return self._commands
