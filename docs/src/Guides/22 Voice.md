# Voice Support

So you want to start playing some 🎵tunes🎶 in voice channels? Well let's get that going for you.

First you're going to want to get the voice dependencies installed:
```
pip install dis-snek[voice]
```
Also, make sure you have installed [FFmpeg](https://ffmpeg.org/) and made it available in the root directory.

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

## But what about local music?

If you want to play your own files, you can do that too! Create an `AudioVolume` object and away you go.

!!! note
    If your audio is already encoded, use the standard `Audio` object instead. You'll lose volume manipulation, however.

```python
import dis_snek
from dis_snek.api.voice.audio import AudioVolume

@dis_snek.slash_command("play", "play a song!")
async def play_file(ctx: dis_snek.InteractionContext):
    audio = AudioVolume("some_file.wav")
    await ctx.voice_state.play(audio)
```

Check out [Active Voice State](/API Reference/models/Snek/active_voice_state/) for a list of available methods and attributes.
