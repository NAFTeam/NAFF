# Events

Events are dispatched whenever a subscribed event gets send by discord.

## What Events Can I Get

What events you subscribe to are defined at startup by setting your `Intents`. 

`Intents.DEFAULT` is a good place to start if your bot is new and small, otherwise it is recommended to take your time and go through them one by one.
```python
bot = Snake(intents=Intents.DEFAULT)
bot.start("Put your token here")
```

For more information, please visit the API reference [here](/API Reference/enums/#dis_snek.models.enums.Intents).

## Hey Listen!!!

Now you can receive events. To respond to them, you need to register a callback. Callbacks should be lower-case, use `_` instead of spaces and start with `on_`.
Depending on how you register your callbacks that's not a requirement, but it is good habit nonetheless.

For example, the event callback for the `ChannelCreate` event should be called `on_channel_create`.

You can find all events and their signatures [here](/API Reference/models/events/discord/).

Be aware that your `Intents` must be set to receive the event you are looking for.

---

There are three ways to register events. **Subclassing** is the recommended way to do this.

=== ":one: Subclassing"
    Here, we are simply subclassing `Snake`. It's that simple!

    ```python
    class MySnake(Snake):
        async def on_channel_create(event: ChannelCreate):
            # this event is called when a channel is created in a guild where the bot is
            
            print(f"Channel created with name: {event.channel.name}")

    bot = MySnake(intents=Intents.DEFAULT)
    bot.start("Put your token here")
    ```

=== ":two: Decorators"
    To use decorators, they need to be in the same file where you defined your `bot = Snake()`.

    ```python
    bot = Snake(intents=Intents.DEFAULT)

    @listen()
    async def on_channel_create(event: ChannelCreate):
        # this event is called when a channel is created in a guild where the bot is
        
        print(f"Channel created with name: {event.channel.name}")

    bot.start("Put your token here")
    ```

=== ":three: Manual Registration"
    You can also register the events manually. This gives you the most flexibility, but it's not the cleanest.

    ```python
    async def on_channel_create(event: ChannelCreate):
        # this event is called when a channel is created in a guild where the bot is
        
        print(f"Channel created with name: {event.channel.name}")


    bot = Snake(intents=Intents.DEFAULT)
    bot.add_listener(Listener(func=on_channel_create, event="on_channel_create"))
    bot.start("Put your token here")
    ```
