# GenLayer · Many Minds

A 72-second motion graphic for the thread *"Why does @GenLayer use multiple AI models instead of just one?"*.
1920×1080, 30 fps, with a synthesized soundtrack. Colors: `#ff87ff`, `#dc00ff` and a pale green `#b3ffcb`.

| Time | Chapter | Thread part |
|---|---|---|
| 0:00 | Intro: the GenLayer logo draws itself and lands with a shockwave | title |
| 0:04 | "Why does GenLayer use **multiple AI models**?" / "The smartest AI **can be wrong**" | hook |
| 0:13 | 01 The problem: one AI chip hallucinates, misreads data and gets prompt-injected, then shatters into **single point of failure** | 1/ |
| 0:25 | 02 The GenLayer way: the logo spawns five validators that each evaluate the decision | 2/ |
| 0:33 | 03 Why it matters: different models catch different mistakes, reliance drops from 100% to 20%, a hacked model gets outvoted | 3/ |
| 0:46 | 04 Optimistic Democracy: the leader proposes, a validator challenges, the appeal brings in more validators, then the result is final | 4/ |
| 0:56 | 05 The goal: ~~infallible~~; one model gives an answer, then a network evaluates it | 5/ |
| 1:05 | Outro: "That's the idea behind GenLayer" | end |

## Files

- `index.html` is the animation and a small player (play, scrub, sound). Every frame is a pure function of time, `window.renderAt(t)`.
- `audio/make_soundtrack.py` synthesizes the music and sound effects with numpy. It reads the cue list from `index.html`, so hits, glitches and whooshes land on the same frames as the picture.
- `tools/render.mjs` renders stills or the full video with headless Chromium and ffmpeg.
- `assets/genlayer-logo-reference.png` is the official mark, which the vector logo in `index.html` was traced from.

## Rebuild the video

```sh
python3 audio/make_soundtrack.py
ffmpeg -y -i audio/genlayer-soundtrack.wav -b:a 192k audio/genlayer-soundtrack.mp3
node tools/render.mjs video 30          # out/genlayer-silent.mp4
ffmpeg -y -i out/genlayer-silent.mp4 -i audio/genlayer-soundtrack.wav \
  -c:v copy -c:a aac -b:a 192k -shortest -movflags +faststart genlayer-many-minds.mp4
```

To preview in a browser, serve the folder (for example `npx serve .`) and open `index.html`.
