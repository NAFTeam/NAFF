# Migration From discord.py

1. Dis-Snek requires python 3.10 (as compared to dpy's 3.5), you may need to upgrade python.
  - If you see `ERROR: Could not find a version that satisfies the requirement dis_snek (from versions: none)` when trying to `pip install dis-snek`, this is your problem.
2. Classes/Models
  - Your client is `dis_snek.Snake`.  (Note that commands are a first-class feature, so this is a replacement to both `discord.Client` and `discord.ext.commands.Bot`)
  - Cogs are `Scales`.
  - `Member` is not a subclass of `User`, if you're using `isinstance`, you'll want to check both explicitly.
3. Scales (Cogs)
  - These work mostly the same, with a few notable changes:
  - Your setup function doesn't need to do `bot.add_cog()`.  Simply call `MyCog(bot)`, and it'll automatically register itself.
  - Scales already define `self.bot`, you don't need to do that in your `__init__` function.
  - For a full example, see [here](/Guides/20 Scales/)
4. Event handlers
  - Register event handlers with `@dis_snek.listen`
  - Where possible, we use the official names for events, most notably `on_message_create` instead of dpy's `on_message`.
    - A full list can be found [here](/API Reference/events/discord/).
  - Event details are stored on a model, passed as a single parameter. (eg: `on_member_update(before, after)` becomes `on_member_update(event)`, where event has a `.before` and `.after`.
  - For more details, read [the Events guide](/Guides/10 Events).
5. Migrating your commands
  - If you were already using dpy's command extension, migrating to slash commands is fairly simple.  You just need to convert the decorators as per the [Slash Commands guide](/Guides/03 Creating Commands/)
  - If you wish to keep using message commands, you can get simple support (no converters) with the `@dis_snek.message_command` decorator, or use [our experimental message command extension](https://github.com/Discord-Snake-Pit/molter)
  - If you were manually handling commands with `on_message`, you'll probably need to figure it out yourself, as this guide doesn't know how you wrote your parser.  Consider using the provided command handlers.

??? Note
    This guide was written based on the experiences of porting a small handful of bots.  There may be gotchas that we did not encounter.  If you run into anything you'd like to have known, let us know in our Discord, and we'll add it to this document.
