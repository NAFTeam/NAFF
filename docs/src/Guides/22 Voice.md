# Voice Support

So you want to start playing some 🎵tunes🎶 in voice channels? Well let's get that going for you.

First you're going to want to get the voice dependencies installed:
```
pip install dis-snek[voice]
```
Now you've got those; let's make a simple play command to get you started.

```python
import dis_snek
from dis_snek.api.voice.audio import YTDLAudio

@dis_snek.slash_command("play", "play a song!")
@dis_snek.slash_option("song", "The song to play", 3, True)
async def play(self, ctx: dis_snek.InteractionContext, song: str):
    if not ctx.voice_state:
        # if we haven't already joined a voice channel
        # join the authors vc
        await ctx.author.voice.channel.connect()

    # Get the audio using YTDL
    audio = await YTDLAudio.from_url(song)
    await ctx.send(f"Now Playing: **{audio.entry['title']}**")
    # Play the audio
    await ctx.voice_state.play(audio)
```

Now just join a voice channel, and type run the "play" slash command with a song of your choice.

Congratulations! You've got a music-bot.

Check out [Active Voice State](/API Reference/models/Snek/active_voice_state/) for a list of available methods and attributes.
