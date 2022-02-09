# Scales

Damn, your code is getting pretty messy now, huh? Wouldn't it be nice if you could organise your commands and listeners into separate files?

Well let me introduce you to `Scales`<br>
Scales allow you to split your commands and listeners into separate files to allow you to better organise your project,
as well as that, they allow you to reload Scales without having to shut down your bot.

Sounds pretty good right? Well, let's go over how you can use them:

## Usage

Below is an example of a bot, one with scales, one without.

??? Hint "Example Usage:"
    === "Without Scales"
        ```python
        # File: `main.py`
        import logging

        import dis_snek.const
        from dis_snek.client import Snake
        from dis_snek.models.application_commands import slash_command, slash_option
        from dis_snek.models.command import message_command
        from dis_snek.models.context import InteractionContext
        from dis_snek.models.discord_objects.components import Button, ActionRow
        from dis_snek.models.enums import ButtonStyles
        from dis_snek.models.enums import Intents
        from dis_snek.models.events import Component
        from dis_snek.models.listener import listen

        logging.basicConfig()
        cls_log = logging.getLogger(dis_snek.const.logger_name)
        cls_log.setLevel(logging.DEBUG)

        bot = Snake(intents=Intents.DEFAULT, sync_interactions=True, asyncio_debug=True)


        @listen()
        async def on_ready():
            print("Ready")
            print(f"This bot is owned by {bot.owner}")


        @listen()
        async def on_guild_create(event):
            print(f"guild created : {event.guild.name}")


        @listen()
        async def on_message_create(event):
            print(f"message received: {event.message.content}")


        @listen()
        async def on_component(event: Component):
            ctx = event.context
            await ctx.edit_origin("test")


        @message_command()
        async def multiple_buttons(ctx):
            await ctx.send(
                "2 buttons in a row",
                components=[Button(ButtonStyles.BLURPLE, "A blurple button"), Button(ButtonStyles.RED, "A red button")],
            )


        @message_command()
        async def action_rows(ctx):
            await ctx.send(
                "2 buttons in 2 rows, using nested lists",
                components=[[Button(ButtonStyles.BLURPLE, "A blurple button")], [Button(ButtonStyles.RED, "A red button")]],
            )


        @message_command()
        async def action_rows_more(ctx):
            await ctx.send(
                "2 buttons in 2 rows, using explicit action_rows lists",
                components=[
                    ActionRow(Button(ButtonStyles.BLURPLE, "A blurple button")),
                    ActionRow(Button(ButtonStyles.RED, "A red button")),
                ],
            )


        bot.start("Token")
        ```

    === "With Scales"
        ```python
        # File: `main.py`
        import logging

        import dis_snek.const
        from dis_snek.client import Snake
        from dis_snek.models.context import ComponentContext
        from dis_snek.models.enums import Intents
        from dis_snek.models.events import Component
        from dis_snek.models.listener import listen


        logging.basicConfig()
        cls_log = logging.getLogger(dis_snek.const.logger_name)
        cls_log.setLevel(logging.DEBUG)

        bot = Snake(intents=Intents.DEFAULT, sync_interactions=True, asyncio_debug=True)


        @listen()
        async def on_ready():
            print("Ready")
            print(f"This bot is owned by {bot.owner}")


        @listen()
        async def on_guild_create(event):
            print(f"guild created : {event.guild.name}")


        @listen()
        async def on_message_create(event):
            print(f"message received: {event.message.content}")


        @listen()
        async def on_component(event: Component):
            ctx = event.context
            await ctx.edit_origin("test")


        bot.grow_scale("test_components")
        bot.start("Token")

        ```
        ```python

        # File: `test_components.py`

        from dis_snek.models.command import message_command
        from dis_snek.models.discord_objects.components import Button, ActionRow
        from dis_snek.models.enums import ButtonStyles
        from dis_snek.models.scale import Scale


        class ButtonExampleSkin(Scale):
            @message_command()
            async def blurple_button(self, ctx):
                await ctx.send("hello there", components=Button(ButtonStyles.BLURPLE, "A blurple button"))

            @message_command()
            async def multiple_buttons(self, ctx):
                await ctx.send(
                    "2 buttons in a row",
                    components=[Button(ButtonStyles.BLURPLE, "A blurple button"), Button(ButtonStyles.RED, "A red button")],
                )

            @message_command()
            async def action_rows(self, ctx):
                await ctx.send(
                    "2 buttons in 2 rows, using nested lists",
                    components=[[Button(ButtonStyles.BLURPLE, "A blurple button")], [Button(ButtonStyles.RED, "A red button")]],
                )

            @message_command()
            async def action_rows_more(self, ctx):
                await ctx.send(
                    "2 buttons in 2 rows, using explicit action_rows lists",
                    components=[
                        ActionRow(Button(ButtonStyles.BLURPLE, "A blurple button")),
                        ActionRow(Button(ButtonStyles.RED, "A red button")),
                    ],
                )


        def setup(bot):
            ButtonExampleSkin(bot)
        ```

Scales are effectively just another python file that contains a class that inherits from an object called `Scale`,
inside this scale, you can put whatever you would like. And upon loading, the contents are added to the bot.

```python
from dis_snek import Scale

class SomeClass(Scale):
    ...

def setup(bot):
    # This is called by dis-snek so it knows how to load the Scale
    SomeClass(bot)
```
As you can see, there's one extra bit, a function called `setup`, this function acts as an entry point for dis-snek,
so it knows how to load the scale properly.

To load a scale, you simply add the following to your `main` script, just above `bot.start`:
```python
...

bot.grow_scale("Filename_here")

bot.start("token")
```

Finally, for the cool bit of Scales, reloading. Scales allow you to edit your code, and reload it, without restarting the bot.
To do this, simply run `bot.regrow_scale("Filename_here")` and your new code will be used. Bare in mind any tasks your scale
is doing will be abruptly stopped.
