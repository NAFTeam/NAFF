# Creating Context Menus

Context menus are interactions under the hood. Defining them is very similar.
Context menus work of `ctx.target_id` which contains the id of the object the user interacted with.

You can also define `scopes` and `permissions` for them, just like with interactions.

For more information, please visit the API reference [here](/API Reference/models/Internal Models/application commands/#dis_snek.models.application_commands.context_menu).

## Message Context Menus

These open up if you right-click a message and choose `Apps`.

This example repeats the selected the message:
```python
@context_menu(name="repeat", context_type=CommandTypes.MESSAGE)
async def repeat(ctx: InteractionContext):
    message = await ctx.channel.get_message(ctx.target_id)
    await ctx.send(message.content)
```

## User Context Menus

These open up if you right-click a user and choose `Apps`.

This example pings the user:
```python
@context_menu(name="ping", context_type=CommandTypes.USER)
async def ping(ctx: InteractionContext):
    member = await ctx.guild.get_member(ctx.target_id)
    await ctx.send(member.mention)
```
