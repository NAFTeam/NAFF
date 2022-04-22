# Creating Prefixed Commands

Prefixed commands, sometimes called "text-based commands" or even "message commands" (not to be confused with Context Menu Message Commands), are commands that are triggered when a user sends a normal message with a designated "prefix" in front of them.

While slash commands have been released, and is typically the way you should be making commands these days, there are many cases where the "legacy" commands may want to be kept due to various reasons, like wanting to use types not well-supported by Discord or to allow for greater flexibility for permission handling.

Whatever the reason is, `Dis-Snek` has an extensive yet familiar prefixed command architecture ready to be used.

## Your First Prefixed Command

To create a prefixed command, simply define an asynchronous function and use the `@prefixed_command()` decorator above it.
```python
@prefixed_command(name="my_command")
async def my_command_function(ctx: PrefixedContext):
    await ctx.reply("Hello world!")
```

??? note "Command Name"
    If `name` is not specified, `Dis-Snek` will automatically use the function's name as the command's name.

If the bot's prefix was set to `!`, then a user could invoke it like:
```
!my_command
```

## Parameters

Often, when using prefixed commands, you typically want to parse in what the user says into seperated parameters/arguments. This can be done easily in this library using a Python-esque syntax.

For example, to make a command that takes in one argument, we can do:
```python
@prefixed_command()
async def test(ctx: PrefixedContext, arg):
    await ctx.reply(arg)
```

When a user uses the command, all they simply need to do is pass a word after the command:
(insert picture of running the above command with one word)

If the user wishes to use multiple words in an argument like this, they can wrap it in quotes like so:
(ditto, but using something "hello world!" for the arg)

!!! warning "Forgetting Quotes"
    If a user forgets or simply does not wrap multiple words in an argument in quotes, the library will only use the first word for the argument and ignore the rest.
    (same as other two, but with hello world, letting the above warning play out or something)

You can add as many parameters as you want to a command:
```python
@prefixed_command()
async def test(ctx: PrefixedContext, arg1, arg2):
    await ctx.reply(f"Arguments: {arg1}, {arg2}.")
```

### Variable and Keyword-Only Arguments

There may be times where you wish for an argument to be able to have multiple words without wrapping them in quotes. There are two ways of apporaching this.

#### Variable

If you wish to get a list (or more specifically, a tuple) of words for one argument, or simply want an undetermined amount of arguments for a command, then you should use a *variable* argument:
```python
@prefixed_command()
async def test(ctx: PrefixedContext, *args):
    await ctx.reply(f"{len(args)} arguments: {','.join(args)}")
```

The result looks something like this:
(insert picture of running "!test hello there world, "how are you?"")

Notice how the quoted words are still parsed as one argument in the tuple.

#### Keyword-Only

If you simply wish to take in the rest of the user's input as an argument, you can use a keyword-only argument, like so:
```python
@prefixed_command()
async def test(ctx: PrefixedContext, *, arg):
    await ctx.reply(arg)
```

The result looks like this:
("!test hello world!")

??? note "Quotes"
    If a user passes quotes into a keyword-only argument, then the resulting argument will have said quotes.
    (show example of "!test "hello world"" here)

!!! warning "Parser ambiguities"
    Due to parser ambiguities, you can *only* have either a single variable or keyword-only/consume rest argument.

## Typehinting and Converters
