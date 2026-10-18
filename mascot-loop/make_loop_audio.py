"""Synthesize a seamless 6 s music loop for the mascot animation.

Every sound is placed on a circular buffer (anything past the end wraps to the
start) and the reverb is a circular convolution, so the WAV loops with no
click or gap. Sound effects sit on the same times as the face timeline in
index.html: blinks, heart pops, the glitch and the wink sparkle.

    python3 mascot-loop/make_loop_audio.py      # writes out/mascot-loop.wav

Requires only numpy.
"""
import os
import wave

import numpy as np

HERE = os.path.dirname(os.path.abspath(__file__))
OUT = os.path.join(HERE, "..", "out")
SR = 44100
DUR = 6.0                      # must match DUR in index.html
BEAT = 0.5                     # 120 BPM: 12 beats, three bars of 4/4
N = int(SR * DUR)
rng = np.random.default_rng(5)

L = np.zeros(N)
R = np.zeros(N)
send = np.zeros(N)


def place(sig, at, gain=1.0, pan=0.0, verb=0.0):
    """Mix a mono signal in at `at` seconds; whatever runs past the end wraps around."""
    i = (int(round(at * SR)) + np.arange(len(sig))) % N
    s = sig * gain
    np.add.at(L, i, s * np.sqrt(0.5 * (1 - pan)))
    np.add.at(R, i, s * np.sqrt(0.5 * (1 + pan)))
    np.add.at(send, i, s * verb)


def tt(dur):
    return np.arange(int(dur * SR)) / SR


def env(dur, attack, tau):
    x = tt(dur)
    e = np.exp(-np.maximum(0, x - attack) / tau)
    return e * np.clip(x / max(attack, 1e-4), 0, 1)


def hz(midi):
    return 440.0 * 2 ** ((midi - 69) / 12)


def lowpass(x, cutoff):
    X = np.fft.rfft(x)
    f = np.fft.rfftfreq(len(x), 1 / SR)
    X *= 1 / (1 + (f / cutoff) ** 4)
    return np.fft.irfft(X, len(x))


# ---- music ----
CHORDS = [  # (start beat, midi notes): Dbmaj9 -> Ebadd9 (happy) -> Cm9
    (0, [49, 56, 60, 63, 65]),
    (4, [51, 58, 62, 65, 70]),
    (8, [48, 55, 58, 62, 63]),
]
for b0, notes in CHORDS:
    dur = 4 * BEAT
    x = tt(dur + 0.6)
    e = np.clip(x / 0.15, 0, 1) * np.clip((dur + 0.6 - x) / 0.6, 0, 1)
    pad = np.zeros(len(x))
    for n in notes[1:]:
        for det in (-0.12, 0.12):
            f = hz(n + det)
            pad += sum(np.sin(2 * np.pi * f * h * x + h) / h ** 1.6 for h in range(1, 6))
    place(lowpass(pad * e, 1400), b0 * BEAT - 0.3, 0.018, verb=0.5)
    # bass on beats 1 and 3 of the bar
    for k in (0, 2):
        d = 0.42
        place(np.sin(2 * np.pi * hz(notes[0] - 12) * tt(d)) * env(d, 0.005, 0.18), (b0 + k) * BEAT, 0.32)
    # bright arp, 8th notes walking up the chord
    for k in range(8):
        n = notes[1:][k % 4] + 12 * (k // 4)
        d = 0.24
        x = tt(d)
        pl = (np.sign(np.sin(2 * np.pi * hz(n) * x)) * 0.5 + np.sin(2 * np.pi * hz(n + 12) * x)) * env(d, 0.002, 0.06)
        place(lowpass(pl, 4200), (b0 + k * 0.5) * BEAT, 0.05, pan=0.45 * np.sin(k * 1.3), verb=0.35)

# drums
for b in range(12):
    if b % 2 == 0:                                             # soft kick
        d = 0.3
        x = tt(d)
        f = 48 + 90 * np.exp(-x / 0.03)
        place(np.sin(2 * np.pi * np.cumsum(f) / SR) * env(d, 0.001, 0.09), b * BEAT, 0.55)
    else:                                                      # snap
        d = 0.2
        nz = lowpass(rng.standard_normal(int(d * SR)), 6000) * env(d, 0.001, 0.04)
        place(nz, b * BEAT, 0.12, verb=0.4)
    for h in (0, 0.5):                                         # closed hats
        d = 0.06
        nz = rng.standard_normal(int(d * SR))
        nz = nz - lowpass(nz, 7000)
        place(nz * env(d, 0.0005, 0.012), (b + h) * BEAT, 0.05 if h else 0.035, pan=0.3)

# ---- sound effects on the face timeline ----
def blip(f0, f1, d=0.08):
    x = tt(d)
    f = f0 * (f1 / f0) ** (x / d)
    return np.sin(2 * np.pi * np.cumsum(f) / SR) * env(d, 0.002, d / 3)


for at in (0.72, 1.86, 5.36):                                   # blinks
    place(blip(1400, 900, 0.07), at, 0.08, pan=0.1)
for at, pan in ((2.2, 0.4), (2.45, -0.4), (2.6, 0.1)):          # heart pops
    place(blip(500, 1700, 0.12), at, 0.13, pan=pan, verb=0.4)
for at, pan in ((1.15, -0.5), (4.3, 0.5)):                      # ear twitches
    place(blip(2600, 2000, 0.03), at, 0.05, pan=pan)
# glitch: bit-crushed noise with a pitch stutter
d = 0.24
x = tt(d)
g = np.sign(np.sin(2 * np.pi * (300 + 900 * (np.floor(x * 40) % 3)) * x)) * 0.5 + rng.standard_normal(len(x)) * 0.5
g = np.round(g * 4) / 4 * np.clip(x / 0.01, 0, 1) * np.clip((d - x) / 0.03, 0, 1)
place(g, 3.86, 0.07)
# wink sparkle: a little bell
d = 0.9
x = tt(d)
bell = sum(np.sin(2 * np.pi * hz(96) * r * x) * a for r, a in ((1, 1), (2.76, 0.4), (5.4, 0.2))) * env(d, 0.002, 0.22)
place(bell, 4.1, 0.06, pan=0.35, verb=0.6)

# ---- circular reverb ----
ir_n = int(1.6 * SR)
ir = rng.standard_normal(ir_n) * np.exp(-np.arange(ir_n) / SR / 0.45)
ir = lowpass(ir, 5000)
ir /= np.sqrt(np.sum(ir ** 2))
IR = np.zeros(N)
IR[:ir_n] = ir
wet = np.fft.irfft(np.fft.rfft(send) * np.fft.rfft(IR), N)
wet_r = np.roll(wet, int(0.013 * SR))
L += wet * 0.35
R += wet_r * 0.35

mix = np.stack([L, R], 1)
mix = np.tanh(mix * 1.2) / np.tanh(1.2)
mix *= 0.89 / np.max(np.abs(mix))
os.makedirs(OUT, exist_ok=True)
path = os.path.join(OUT, "mascot-loop.wav")
with wave.open(path, "wb") as w:
    w.setnchannels(2)
    w.setsampwidth(2)
    w.setframerate(SR)
    w.writeframes((mix * 32767).astype("<i2").tobytes())
print("wrote", path)
