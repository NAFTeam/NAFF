# Converters

If your bot is complex enough, you might find yourself wanting to use custom models in your commands. Converters are classes that allow you to do just that, and can be used in both slash and prefixed commands.

This can be useful if you frequently find yourself starting commands with `thing = lookup(thing_name)`

## Inline Converters

If you do not wish to create an entirely new class, you can simply add a `convert` function in your existing class:

```python
class DatabaseEntry():
    name: str
    description: str
    score: int

    @classmethod
    async def convert(cls, ctx: Context, value: str) -> DatabaseEntry:
        """This is where the magic happens"""
        return cls(hypothetical_database.lookup(ctx.guild.id, value))

@slash_command(name="lookup", description="Gives info about a thing from the db")
@slash_option(
    name="thing",
    description="The user enters a string",
    required=True,
    opt_type=OptionTypes.STRING
)
async def my_command_function(ctx: InteractionContext, thing: DatabaseEntry):
    await ctx.send(f"***{thing.name}***\n{thing.description}\nScore: {thing.score}/10")
```

As you can see, a converter can transparently convert what Discord sends you (a string, a user, etc) into something more complex (a pokemon card, a scoresheet, etc).

## `Converter`

You may also use the `Converter` class that `Dis-Snek` has as well.

```python
class UpperConverter(Converter):
    async def convert(ctx: PrefixedContext, argument: str):
        return argument.upper()

@prefixed_command()
async def upper(ctx: PrefixedContext, uppered: UpperConverter):
    await ctx.reply(uppered)
```

There are also `Converter`s that represent some Discord models that you can subclass from. These are largely useful for prefixed commands, so a list of those converters is kept [there](/Guides/07 Creating Prefixed Commands).
