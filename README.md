[![PyPI](https://img.shields.io/pypi/v/dis-snek)](https://pypi.org/project/dis-snek/)
[![Downloads](https://static.pepy.tech/personalized-badge/dis-snek?period=total&units=abbreviation&left_color=grey&right_color=green&left_text=pip%20installs)](https://pepy.tech/project/dis-snek)
[![Code style: black](https://img.shields.io/badge/code%20style-black-000000.svg)](https://github.com/psf/black)
[![black-formatted](https://img.shields.io/github/workflow/status/Discord-Snake-Pit/dis-snek/black-action/master?label=Black%20Format&logo=github)](https://github.com/LordOfPolls/dis_snek/actions/workflows/black.yml)
[![CodeQL](https://img.shields.io/github/workflow/status/Discord-Snake-Pit/dis-snek/CodeQL/master?label=CodeQL&logo=Github)](https://github.com/LordOfPolls/dis_snek/actions/workflows/codeql-analysis.yml)
[![Discord](https://img.shields.io/discord/870046872864165888?color=%235865F2&label=Server&logo=discord&logoColor=%235865F2)](https://discord.gg/hpfNhH8BsY)
[![Documentation Status](https://readthedocs.org/projects/dis-snek/badge/?version=latest)](https://dis-snek.readthedocs.io/en/latest/?badge=latest)

# What is this?
This is `Dis-Snek`, a python API wrapper for Discord.
Snek is intended to be fast, easy to use, and easily modified to suit your needs.

### Features:
- ✅ 100% coverage of the application commands API
- ✅ Dynamic cache with TTL support
- ✅ Modern and Pythonic API
- ✅ Proper rate-limit handling
- ✅ Feature parity with most other Discord API wrappers

## Is this just another `Discord.py` fork?
While this library shares features and some stylistic choices with `discord.py`, it is completely separate from them. We think `discord.py` is a fantastic library, but we disagree with the direction and design decisions that were made by it.

Compared to `discord.py`; `Dis-Snek` starts faster, responds faster, is simpler to use, and comes equipped with plenty of creature comforts to help get your bot launched faster.

## How do I use this?
Here is a basic example:
```python
bot = Snake(sync_interactions=True)

@listen()
async def on_startup():
    print("Ready")
    print(f"This bot is owned by {bot.owner}")

@message_command()
    async def blurple_button(self, ctx):
        await ctx.send("hello there", components=Button(ButtonStyles.BLURPLE, "A blurple button"))

@context_menu(name="user menu", context_type=CommandTypes.USER, scopes=701347683591389185)
    async def user_context(self, ctx):
        await ctx.send("Context menu:: user")


bot.start("Token")
```
For more examples check out [our examples repo](https://github.com/Discord-Snake-Pit/examples) or the [docs](https://dis-snek.readthedocs.io/), and if you get stuck join our [Discord server](https://discord.gg/dis-snek)


## "Can I contribute to this project?"
Of course, we welcome all contributions to this library. Just ensure you follow our [requirements]().
If youre stuck for things to contribute, check out our [Trello](https://trello.com/b/LVjnmYKt/dev-board) for inspiration.

## Links:
- Support Server: https://discord.gg/dis-snek
- Documentation:  https://dis-snek.rtfd.io/
- Trello: https://trello.com/b/LVjnmYKt/dev-board
