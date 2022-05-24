# Voice Support

So you want to start playing some 🎵tunes🎶 in voice channels? Well let's get that going for you.

First you're going to want to get the voice dependencies installed:
```
pip install dis-snek[voice]
```

Then you'll need to download [FFmpeg](https://ffmpeg.org) and place it in your project directory or PATH.

Now you've got those; let's make a simple play command to get you started.

```python
import naff
from naff.api.voice.audio import YTDLAudio


@naff.slash_command("play", "play a song!")
@naff.slash_option("song", "The song to play", 3, True)
async def play(self, ctx: naff.InteractionContext, song: str):
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

## But what about local music?

If you want to play your own files, you can do that too! Create an `AudioVolume` object and away you go.

!!! note
    If your audio is already encoded, use the standard `Audio` object instead. You'll lose volume manipulation, however.

```python
import naff
from naff.api.voice.audio import AudioVolume


@naff.slash_command("play", "play a song!")
async def play_file(ctx: naff.InteractionContext):
    audio = AudioVolume("some_file.wav")
    await ctx.voice_state.play(audio)
```

Check out [Active Voice State](/API Reference/models/naff/active_voice_state/) for a list of available methods and attributes.
