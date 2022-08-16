[![PyPI](https://img.shields.io/pypi/v/naff)](https://pypi.org/project/naff/)
[![Downloads](https://static.pepy.tech/personalized-badge/dis-snek?period=total&units=abbreviation&left_color=grey&right_color=green&left_text=pip%20installs)](https://pepy.tech/project/dis-snek)
[![Code style: black](https://img.shields.io/badge/code%20style-black-000000.svg)](https://github.com/psf/black)
[![black-formatted](https://img.shields.io/github/workflow/status/NAFTeam/NAFF/black-action/master?label=Black%20Format&logo=github)](https://github.com/NAFTeam/NAFF/actions/workflows/black.yml)
[![CodeQL](https://img.shields.io/github/workflow/status/NAFTeam/NAFF/CodeQL/master?label=CodeQL&logo=Github)](https://github.com/NAFTeam/NAFF/actions/workflows/codeql-analysis.yml)
[![Discord](https://img.shields.io/discord/870046872864165888?color=%235865F2&label=Server&logo=discord&logoColor=%235865F2)](https://discord.gg/naff)
[![Documentation Status](https://readthedocs.org/projects/naff-docs/badge/?version=latest)](https://naff-docs.readthedocs.io/en/latest/?version=latest)

# What is this?
This is `NAFF`, a python API wrapper for Discord.
NAFF is intended to be fast, easy to use, and easily modified to suit your needs.

### Features:
- ✅ 100% coverage of the application commands API
- ✅ Dynamic cache with TTL support
- ✅ Modern and Pythonic API
- ✅ Proper rate-limit handling
- ✅ Feature parity with most other Discord API wrappers

## Is this just another `Discord.py` fork?
While this library shares features and some stylistic choices with `discord.py`, it is completely separate from them. We think `discord.py` is a fantastic library, but we disagree with the direction and design decisions that were made by it.

## How do I use this?
Here is a basic example:

```python
from naff import Client, Button, ButtonStyles, CommandTypes, context_menu, prefixed_command, listen

bot = Client(sync_interactions=True)


@listen()
async def on_startup():
    print("Ready")
    print(f"This bot is owned by {bot.owner}")


@prefixed_command()
async def test_button(ctx):
    await ctx.send("Blurple button example!", components=Button(ButtonStyles.BLURPLE, "Click me"))


@context_menu(name="User menu", context_type=CommandTypes.USER, scopes=[931832853770149918])
async def user_context(ctx):
    await ctx.send("Context menu example!", ephemeral=True)


bot.start("TOKEN")
```
For more examples check out [our examples repo](https://github.com/NAFTeam/examples) or the [docs](https://naff-docs.readthedocs.io/). You also can [explore projects with the `NAFF` topic](https://github.com/topics/naff) or older [`dis-snek` topic](https://github.com/topics/dis-snek).

If you get stuck join our [Discord server](https://discord.gg/naff).


## "Can I contribute to this project?"
Of course, we welcome all contributions to this library. Just ensure you follow our [requirements](/CONTRIBUTING.md).
If youre stuck for things to contribute, check out our [GitHub Projects](https://github.com/orgs/NAFTeam/projects/1) for inspiration.

## Links:
- Support Server: https://discord.gg/naff
- Documentation:  https://naff-docs.readthedocs.io/en/latest/
