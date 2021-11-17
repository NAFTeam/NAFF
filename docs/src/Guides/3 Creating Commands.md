# Creating Slash Commands

So you want to make a slash command (or interaction, as they are officially called), but don't know how to get started? 
Then this is the right place for you.

## Your First Command

To create an interaction, simply define an asynchronous function and use the `@slash_command()` decorator above it.

Interactions need to be responded to within 3 seconds. To do this, use `await ctx.send()`. 
If your code needs more time, don't worry. You can use `await ctx.defer()` to increase the time until you need to respond to the command to 15 minutes.
```python
@slash_command(name="my_command", description="My first command :)")
async def my_command_function(ctx: InteractionContext):
    await ctx.send("Hello World")

@slash_command(name="my_long_command", description="My second command :)")
async def my_long_command_function(ctx: InteractionContext):
    # need to defer it, otherwise it fails
    await ctx.defer()
    
    # do stuff for a bit
    await asyncio.sleep(600)
    
    await ctx.send("Hello World")
```

Interactions can either be global, or limited to specific guilds. 
Global commands take up to an hour to sync with Discord and show up, so don't worry when you first register a command.

When testing, it is recommended to use non-global commands, as they sync instantly.
For that, you can either define `scopes` in every command, or set `debug_scope` in the bot instantiation which sets the scope automatically for all commands.

You define non-global commands by passing a list of guild ids to `scopes` in the interaction creation.
```python
@slash_command(name="my_command", description="My first command :)", scopes=[870046872864165888])
async def my_command_function(ctx: InteractionContext):
    await ctx.send("Hello World")
```

For more information, please visit the API reference [here](/API Reference/models/Internal Models/application commands/#dis_snek.models.application_commands.slash_command).

## Subcommands

If you have multiple commands that fit under the same category, subcommands are perfect for you.

Let's define a basic sub command:
```python
@slash_command(
    name="base", 
    description="My command base",
    group_name="group",
    group_description="My command group",
    sub_cmd_name="command",
    sub_cmd_description="My command",
)
async def my_command_function(ctx: InteractionContext):
    await ctx.send("Hello World")
```

This will show up in discord as `/base group command`. There are two ways to add additional subcommands:

=== ":one: Decorator"
    ```python
    @my_command_function.subcommand(sub_cmd_name="second_command", sub_cmd_description="My second command")
    async def my_second_command_function(ctx: InteractionContext):
        await ctx.send("Hello World")
    ```

=== ":two: Repeat Definition"
    ```python
    @slash_command(
        name="base", 
        description="My command base",
        group_name="group",
        group_description="My command group",
        sub_cmd_name="second_command",
        sub_cmd_description="My second command",
    )
    async def my_second_command_function(ctx: InteractionContext):
        await ctx.send("Hello World")
    ```

    **Note:** This is particularly useful if you want to split sub commands into different files.


## But I Need More Options

Interactions can also have options. There are a bunch of different [types of options](/API Reference/models/Internal Models/application commands/#dis_snek.models.application_commands.OptionTypes):

| Option Type | Return Type | Description |
| ------------ | ------------- | ------------- |
| `OptionTypes.STRING` | `str` | Limit the input to a string.  |
| `OptionTypes.INTEGER` | `int` |  Limit the input to a integer.  |
| `OptionTypes.NUMBER` | `float` |  Limit the input to a float. |
| `OptionTypes.BOOLEAN` | `bool` |  Let the user choose either `True` or `False`. |
| `OptionTypes.USER` | `Member` in guilds, else `User` |  Let the user chose a discord user from an automatically generated list of options.  |
| `OptionTypes.CHANNEL` | `GuildChannel` in guilds, else `DMChannel` |  Let the user chose a discord channel from an automatically generated list of options.  |
| `OptionTypes.ROLE` | `Role` |  Let the user chose a discord role from an automatically generated list of options.  |
| `OptionTypes.MENTIONABLE` | `DiscordObject` |  Let the user chose any discord mentionable from an automatically generated list of options.  |

Now that you know all the options you have for options, you can opt into adding options to your interaction.

You do that by using the `@slash_option()` decorator and passing the option name as a function parameter:
```python
@slash_command(name="my_command", ...)
@slash_option(
    name="integer_option", 
    description="Integer Option", 
    required=True, 
    opt_type=OptionTypes.INTEGER
)
async def my_command_function(ctx: InteractionContext, integer_option: int):
    await ctx.send(f"You input {integer_option}")
```

Options can either be required or not. If an option is not required, make sure to set a default value for them.

Always make sure to define all required options first, that is a discord requirement!
```python
@slash_command(name="my_command", ...)
@slash_option(
    name="integer_option", 
    description="Integer Option", 
    required=False, 
    opt_type=OptionTypes.INTEGER
)
async def my_command_function(ctx: InteractionContext, integer_option: int = 5):
    await ctx.send(f"You input {integer_option}")
```

For more information, please visit the API reference [here](/API Reference/models/Internal Models/application commands/#dis_snek.models.application_commands.slash_option).

## Restricting Options

If you are using a `OptionTypes.CHANNEL` option, you can restrict the channel a user can choose by setting `channel_types`:
```python
@slash_command(name="my_command", ...)
@slash_option(
    name="channel_option", 
    description="Channel Option", 
    required=True, 
    opt_type=OptionTypes.CHANNEL, 
    channel_types=ChannelTypes.GUILD_TEXT
)
async def my_command_function(ctx: InteractionContext, channel_option: GUILD_TEXT):
    await channel_option.send("This is a text channel in a guild")
    
    await ctx.send("...")
```

You can also set an upper and lower limit for both `OptionTypes.INTEGER` and `OptionTypes.NUMBER` by setting `min_value` and `max_value`:
```python
@slash_command(name="my_command", ...)
@slash_option(
    name="integer_option", 
    description="Integer Option", 
    required=True, 
    opt_type=OptionTypes.INTEGER, 
    min_value=10, 
    max_value=15
)
async def my_command_function(ctx: InteractionContext, integer_option: int):
    await ctx.send(f"You input {integer_option} which is always between 10 and 15")
```

!!! danger "Option Names"
    Be aware that the option `name` and the function parameter need to be the same (In this example both are `integer_option`)


## But I Want A Choice

If your users ~~are dumb~~ constantly misspell specific strings, it might be wise to set up choices. 
With choices, the user can no longer freely input whatever they want, instead, they must choose from a curated list.

To create a choice, simply fill `choices` in `@slash_option()`. An option can have up to 25 choices:
```python
@slash_command(name="my_command", ...)
@slash_option(
    name="integer_option", 
    description="Integer Option", 
    required=True, 
    opt_type=OptionTypes.INTEGER,
    choices=[
        SlashCommandChoice(name="One", value=1),
        SlashCommandChoice(name="Two", value=2)
    ]
)
async def my_command_function(ctx: InteractionContext, integer_option: int):
    await ctx.send(f"You input {integer_option} which is either 1 or 2")
```

For more information, please visit the API reference [here](/API Reference/models/Internal Models/application commands/#dis_snek.models.application_commands.SlashCommandChoice).

## I Need More Than 25 Choices

Looks like you want autocomplete options. These dynamically show users choices based on their input. 
The downside is that you need to supply the choices on request, making this a bit more tricky to set up.

To use autocomplete options, set `autocomplete=True` in `@slash_option()`:
```python
@slash_command(name="my_command", ...)
@slash_option(
    name="string_option", 
    description="String Option", 
    required=True, 
    opt_type=OptionTypes.STRING,
    autocomplete=True
)
async def my_command_function(ctx: InteractionContext, string_option: str):
    await ctx.send(f"You input {string_option}")
```

Then you need to register the autocomplete callback, aka the function discord calls when users fill in the option.

In there, you have three seconds to return whatever choices you want to the user. In this example we will simply return their input with "a", "b" or "c" appended:
```python
@my_command.autocomplete("string_option")
async def autocomplete(self, ctx: AutocompleteContext, string_option: str):
    # make sure this is done within three seconds
    await ctx.send(
        choices=[
            {
                "name": f"{string_option}a",
                "value": f"{string_option}a",
            },
            {
                "name": f"{string_option}b",
                "value": f"{string_option}b",
            },
            {
                "name": f"{string_option}c",
                "value": f"{string_option}c",
            },
        ]
    )
```

## But I Don't Like Decorators

You are in luck. There are currently four different ways to create interactions, one does not need any decorators at all.

=== ":one: Multiple Decorators"
    ```python
    @slash_command(name="my_command", description="My first command :)")
    @slash_option(
        name="integer_option", 
        description="Integer Option", 
        required=True, 
        opt_type=OptionTypes.INTEGER
    )
    async def my_command_function(ctx: InteractionContext, integer_option: int):
        await ctx.send(f"You input {integer_option}")
    ```

=== ":two: Single Decorator"
    ```python
    @slash_command(
        name="my_command", 
        description="My first command :)",
        options=[
            SlashCommandOption(
                name="integer_option", 
                description="Integer Option", 
                required=True, 
                opt_type=OptionTypes.INTEGER
            )
        ]
    )
    async def my_command_function(ctx: InteractionContext, integer_option: int):
        await ctx.send(f"You input {integer_option}")
    ```

=== ":three: Function Annotations"
    ```python
    @slash_command(name="my_command", description="My first command :)")
    async def my_command_function(ctx: InteractionContext, integer_option: slash_int_option("Integer Option")):
        await ctx.send(f"You input {integer_option}")
    ```

=== ":four: Manual Registration"
    ```python
    async def my_command_function(ctx: InteractionContext, integer_option: int):
        await ctx.send(f"You input {integer_option}")
    
    bot.add_interaction(
        command=SlashCommand(
            name="my_command",
            description="My first command :)",
            options=[
                SlashCommandOption(
                    name="integer_option", 
                    description="Integer Option", 
                    required=True, 
                    opt_type=OptionTypes.INTEGER
                )
            ]
        )
    )
    ```

## I Don't Want My Friends Using My Commands

!!! danger "Interaction Permissions"
    This page is currently missing, and will be populated at a later date. To learn how to use them, please visit their documentation [here](/API Reference/models/Internal Models/application commands/#dis_snek.models.application_commands.slash_permission).


## I Don't Want To Define The Same Option Every Time

If you are like me, you find yourself reusing options in different commands and having to redefine them every time which is both annoying and bad programming.

Luckily, you can simply make your own decorators that themselves call `@slash_option()`:
```python
def my_own_int_option():
    """Call with `@my_own_int_option()`"""

    def wrapper(func):
        return slash_option(
            name="integer_option", 
            description="Integer Option", 
            opt_type=OptionTypes.INTEGER, 
            required=True
        )(func)

    return wrapper


@slash_command(name="my_command", ...)
@my_own_int_option()
async def my_command_function(ctx: InteractionContext, integer_option: int):
    await ctx.send(f"You input {integer_option}")
```

The same principle can be used to reuse autocomplete options.

