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

---

# GenLayer · Mascot Loop

A seamless 6-second 3D loop of the GenLayer cat mascot for avatars, stickers and posts, 1080×1080 at 60 fps. The cat hovers over a turning hex platform in front of a halo of network nodes, wags its tail, twitches its ears and cycles its screen face: **smug → blink → happy (waves, hearts pop out) → glitch → wink → blink → smug**. Every motion is a periodic function of time, so the last frame flows straight back into the first.

| File | What it is |
|---|---|
| `mascot-loop/genlayer-mascot-loop.mp4` | 1080×1080, 60 fps, with the music loop |
| `mascot-loop/genlayer-mascot-loop.gif` | 420×420, 25 fps GIF for chats and READMEs |
| `mascot-loop/genlayer-mascot-loop-hq.gif` | 720×720, 30 fps high-quality GIF made with [gifski](https://gif.ski) (about 29 MB) |
| `mascot-loop/genlayer-mascot-loop-discord.gif` | 540×540, 30 fps, under Discord's 10 MB upload limit (lite render: locked camera, no particles) |
| `mascot-loop/genlayer-mascot-loop-discord-transparent.gif` | 540×540, 30 fps, transparent background, cat and hearts only, under 10 MB |
| `mascot-loop/genlayer-mascot-loop-discord-alpha.gif` | 540×540, 30 fps, the full transparent scene (same as the WebM: platform, halo, particles), under 10 MB |
| `mascot-loop/genlayer-mascot-loop-alpha.webm` | transparent background (VP9 + alpha), for overlays and stickers |
| `mascot-loop/index.html` | the scene (Three.js r170, vendored in `mascot-loop/vendor/`) with a small player |
| `mascot-loop/make_loop_audio.py` | synthesizes the music loop and sound effects (blinks, heart pops, glitch, sparkle) |

The character is built from primitives in code: a cel shader with purple-tinted shadows and a pink/cyan rim, inverted-hull ink outlines, and a face drawn every frame onto a canvas as an LED grid, using the same vector GenLayer mark as the Many Minds video.

## Rebuild the loop

```sh
node tools/render.mjs --page mascot-loop/index.html --size 1080x1080 --scale 2 --out mascot-2160 video 60
python3 mascot-loop/make_loop_audio.py
ffmpeg -y -i out/mascot-2160.mp4 -i out/mascot-loop.wav -vf scale=1080:1080:flags=lanczos \
  -c:v libx264 -preset slow -crf 16 -pix_fmt yuv420p -c:a aac -b:a 192k -shortest -movflags +faststart \
  mascot-loop/genlayer-mascot-loop.mp4
ffmpeg -y -i out/mascot-2160.mp4 -vf "fps=25,scale=420:420:flags=lanczos,split[a][b];[a]palettegen=max_colors=128:stats_mode=diff[p];[b][p]paletteuse=dither=bayer:bayer_scale=4:diff_mode=rectangle" \
  -loop 0 mascot-loop/genlayer-mascot-loop.gif
# high-quality GIF (gifski: https://gif.ski)
mkdir -p out/gif-frames && ffmpeg -i out/mascot-2160.mp4 -vf "fps=30,scale=720:720:flags=lanczos" out/gif-frames/f%04d.png
gifski --fps 30 --quality 90 --width 720 -o mascot-loop/genlayer-mascot-loop-hq.gif out/gif-frames/f*.png
# Discord GIF from the lite render
node tools/render.mjs --page mascot-loop/index.html --size 1080x1080 --query lite --out lite video 30
mkdir -p out/lite-fr && ffmpeg -i out/lite.mp4 -vf "scale=540:540:flags=lanczos" out/lite-fr/f%04d.png
gifski --fps 30 --quality 85 --width 540 -o mascot-loop/genlayer-mascot-loop-discord.gif out/lite-fr/f*.png
# transparent Discord GIF: only the cat (?lite&solo), cropped around it
node tools/render.mjs --page mascot-loop/index.html --size 1080x1080 --query "lite&solo" --alpha --out solo-alpha video 30
mkdir -p out/solo-540 && ffmpeg -framerate 30 -i out/solo-alpha-frames/f%05d.png -vf "crop=880:880:95:0,scale=540:540:flags=lanczos" -pix_fmt rgba out/solo-540/f%04d.png
gifski --fps 30 --quality 90 --width 540 -o mascot-loop/genlayer-mascot-loop-discord-transparent.gif out/solo-540/f*.png
# transparent Discord GIF of the full scene, from the --alpha frames made for the WebM
mkdir -p out/fa-540 && ffmpeg -framerate 30 -i out/mascot-alpha-frames/f%05d.png -vf "scale=540:540:flags=lanczos" -pix_fmt rgba out/fa-540/f%04d.png
python3 tools/hard_alpha.py out/fa-540 90
gifski --fps 30 --quality 90 --width 540 -o mascot-loop/genlayer-mascot-loop-discord-alpha.gif out/fa-540/f*.png
# transparent version
node tools/render.mjs --page mascot-loop/index.html --size 1080x1080 --alpha --out mascot-alpha video 30
ffmpeg -y -framerate 30 -i out/mascot-alpha-frames/f%05d.png -c:v libvpx-vp9 -pix_fmt yuva420p -b:v 0 -crf 30 \
  mascot-loop/genlayer-mascot-loop-alpha.webm
```

To preview, serve the repo root (for example `npx serve .`) and open `mascot-loop/index.html`.
