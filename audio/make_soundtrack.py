"""Synthesize the soundtrack for the GenLayer motion graphic.

Everything is generated from code (no samples). Sound effects follow the cue
list in index.html (the block between /*CUES*/ and /*END*/), so picture and
sound share one timeline; the music bed follows the scene times below.

    python3 audio/make_soundtrack.py          # writes audio/genlayer-soundtrack.wav
    ffmpeg -i audio/genlayer-soundtrack.wav -b:a 192k audio/genlayer-soundtrack.mp3

Requires only numpy.
"""
import json
import os
import re
import wave

import numpy as np

HERE = os.path.dirname(os.path.abspath(__file__))
SRC = open(os.path.join(HERE, "..", "index.html"), encoding="utf-8").read()
block = re.search(r"/\*CUES\*/(.*?)/\*END\*/", SRC, re.S).group(1)
CUES = json.loads(block[block.index("["): block.rindex("]") + 1])
DUR = float(re.search(r"const DUR = ([\d.]+);", SRC).group(1))

SR = 44100
N = int(SR * DUR)
t = np.arange(N) / SR
rng = np.random.default_rng(11)

L = np.zeros(N)
R = np.zeros(N)
send = np.zeros(N)  # reverb bus (mono)


def idx(sec):
    return max(0, min(N, int(sec * SR)))


def place(sig, at, gain=1.0, pan=0.0, verb=0.0):
    """Mix a mono signal into the stereo bus starting at `at` seconds."""
    a = idx(at)
    b = min(N, a + len(sig))
    if b <= a:
        return
    s = sig[: b - a] * gain
    L[a:b] += s * np.sqrt(0.5 * (1 - pan))
    R[a:b] += s * np.sqrt(0.5 * (1 + pan))
    send[a:b] += s * verb


def band(x, lo, hi):
    """Brick-wall band-pass via FFT."""
    X = np.fft.rfft(x)
    f = np.fft.rfftfreq(len(x), 1 / SR)
    X[(f < lo) | (f > hi)] = 0
    return np.fft.irfft(X, len(x))


def env_ad(n, attack, decay_tau):
    tt = np.arange(n) / SR
    e = np.exp(-np.maximum(0, tt - attack) / decay_tau)
    if attack > 0:
        e *= np.clip(tt / attack, 0, 1)
    return e


def sweep(f0, f1, dur):
    n = int(dur * SR)
    k = np.linspace(0, 1, n)
    f = f0 * (f1 / f0) ** k
    return np.sin(2 * np.pi * np.cumsum(f) / SR)


def saw(freq, n, harmonics=8):
    tt = np.arange(n) / SR
    return sum(np.sin(2 * np.pi * freq * h * tt) / h for h in range(1, harmonics + 1))


def square(freq, n):
    return np.sign(np.sin(2 * np.pi * freq * np.arange(n) / SR))


def note(name):
    names = {"C": -9, "C#": -8, "D": -7, "D#": -6, "E": -5, "F": -4, "F#": -3, "G": -2, "G#": -1, "A": 0, "A#": 1, "B": 2}
    pitch, octave = name[:-1], int(name[-1])
    return 440.0 * 2 ** ((names[pitch] + 12 * (octave - 4)) / 12)


def noise(n):
    return rng.standard_normal(n)


# ---------------- instruments ----------------
def kick(gain=1.0):
    n = int(0.42 * SR)
    body = sweep(160, 44, 0.42) * env_ad(n, 0.002, 0.12)
    click = band(noise(n), 1500, 6000) * env_ad(n, 0.0005, 0.004) * 0.3
    return (body + click) * gain


def clap():
    n = int(0.3 * SR)
    x = band(noise(n), 900, 7000)
    e = np.zeros(n)
    for k, off in enumerate([0, 0.011, 0.022]):
        a = int(off * SR)
        e[a:] += env_ad(n - a, 0.0005, 0.012 if k < 2 else 0.07)
    return x * e * 0.7


def hat(open_=False):
    n = int((0.22 if open_ else 0.05) * SR)
    return band(noise(n), 7000, 16000) * env_ad(n, 0.0005, 0.06 if open_ else 0.012)


def bell(f, dur=2.0):
    n = int(dur * SR)
    tt = np.arange(n) / SR
    parts = [(1, 1.0), (2.0, 0.45), (3.01, 0.25), (4.2, 0.15), (5.4, 0.08)]
    return sum(a * np.sin(2 * np.pi * f * m * tt) * np.exp(-tt * (1.6 + m)) for m, a in parts)


def boom(f0=85, f1=26, dur=2.4):
    n = int(dur * SR)
    body = sweep(f0, f1, dur) * env_ad(n, 0.004, 0.7)
    crack = band(noise(n), 60, 4000) * env_ad(n, 0.001, 0.15)
    return np.tanh((body * 1.4 + crack * 0.8) * 1.6)


def pad(freqs, dur, attack=0.8, release=1.2, bright=6):
    n = int(dur * SR)
    tt = np.arange(n) / SR
    x = sum(saw(f, n, bright) + saw(f * 1.005, n, bright) + saw(f * 0.995, n, bright) for f in freqs) / (3 * len(freqs))
    e = np.clip(tt / attack, 0, 1) * np.clip((dur - tt) / release, 0, 1)
    return x * e


def pluck(f, dur=0.22, bright=10):
    n = int(dur * SR)
    return saw(f, n, bright) * env_ad(n, 0.002, 0.06)


def bass(f, dur):
    n = int(dur * SR)
    x = np.tanh(saw(f, n, 6) * 1.5) * 0.6 + np.sin(2 * np.pi * f / 2 * np.arange(n) / SR) * 0.5
    return x * env_ad(n, 0.003, dur * 0.45)


# ---------------- sound effects (driven by the cue list) ----------------
def fx_whoosh(a, at):
    n = int(0.9 * SR)
    x = band(noise(n), 400, 7000) * np.sin(np.linspace(0, np.pi, n)) ** 2
    place(x, at - 0.35, gain=0.16 * a, pan=0.3, verb=0.25)


def fx_riser(a, at, d):
    n = int(d * SR)
    k = np.linspace(0, 1, n) ** 2
    x = band(noise(n), 1200, 12000) * k + sweep(110, 880, d) * k * 0.6
    place(x, at, gain=0.22 * a, verb=0.3)


def fx_impact(a, at):
    place(boom(90, 26, 2.6), at, gain=0.75 * a, verb=0.45)
    place(band(noise(int(0.4 * SR)), 2000, 12000) * env_ad(int(0.4 * SR), 0.001, 0.08), at, gain=0.25 * a, verb=0.5)
    place(bell(note("A6"), 1.6), at + 0.02, gain=0.05 * a, verb=0.8)


def fx_glitch(a, at, d):
    n = int(d * SR)
    x = np.zeros(n)
    step = int(0.022 * SR)
    for s in range(0, n, step):
        e = min(n, s + step)
        r = rng.random()
        if r < 0.45:
            x[s:e] = square(rng.uniform(150, 2400), e - s) * 0.6
        elif r < 0.8:
            x[s:e] = noise(e - s) * 0.5
    x = np.round(x * 6) / 6  # bit-crush
    place(x * env_ad(n, 0.001, d * 0.6 + 0.02), at, gain=0.13 * a, pan=rng.uniform(-0.5, 0.5))


def fx_decode(a, at, d):
    k = 0
    while k * 0.035 < d:
        n = int(0.03 * SR)
        f = rng.choice([note(x) for x in ["A5", "C6", "E6", "G6", "A6", "C7"]])
        place(square(f, n) * env_ad(n, 0.001, 0.01), at + k * 0.035, gain=0.035 * a, pan=rng.uniform(-0.6, 0.6), verb=0.2)
        k += 1


def fx_type(a, at, d):
    k = 0
    while k * 0.05 < d:
        n = int(0.02 * SR)
        place(band(noise(n), 2000, 9000) * env_ad(n, 0.0005, 0.004), at + k * 0.05 + rng.uniform(0, 0.012), gain=0.12 * a, pan=rng.uniform(-0.3, 0.3))
        k += 1


def fx_pop(a, at):
    place(sweep(500, 1300, 0.08) * env_ad(int(0.08 * SR), 0.002, 0.03), at, gain=0.14 * a, pan=rng.uniform(-0.4, 0.4), verb=0.3)


def fx_ping(a, at):
    place(bell(note("E6"), 1.8), at, gain=0.11 * a, verb=0.7)
    place(bell(note("B6"), 1.4), at + 0.07, gain=0.05 * a, verb=0.7)


def fx_ok(a, at):
    for k, nm in enumerate(["E6", "A6"]):
        place(bell(note(nm), 1.2), at + k * 0.06, gain=0.08 * a, verb=0.6)


def fx_blip(a, at):
    place(sweep(1600, 2600, 0.06) * env_ad(int(0.06 * SR), 0.001, 0.02), at, gain=0.12 * a, verb=0.3)


def fx_error(a, at):
    n = int(0.26 * SR)
    x = np.tanh((saw(110, n, 12) + saw(116.5, n, 12)) * 1.2)
    place(band(x, 80, 3500) * env_ad(n, 0.003, 0.12), at, gain=0.16 * a)


def fx_scan(a, at, d):
    n = int(d * SR)
    x = sweep(500, 1900, d) * 0.4 + band(noise(n), 3000, 9000) * 0.3
    place(x * np.sin(np.linspace(0, np.pi, n)), at, gain=0.06 * a, pan=rng.uniform(-0.5, 0.5), verb=0.3)


def fx_power(a, at):
    place(sweep(50, 700, 0.55) * env_ad(int(0.55 * SR), 0.45, 0.12), at, gain=0.16 * a, verb=0.4)
    place(bell(note("A5"), 1.4), at + 0.45, gain=0.06 * a, verb=0.6)


def fx_crack(a, at):
    for k in range(12):
        n = int(0.03 * SR)
        place(np.tanh(band(noise(n), 800, 8000) * 3) * env_ad(n, 0.0005, 0.006), at + rng.uniform(0, 0.45), gain=0.2 * a, pan=rng.uniform(-0.6, 0.6))


def fx_shatter(a, at):
    n = int(1.2 * SR)
    place(band(noise(n), 2500, 14000) * env_ad(n, 0.001, 0.18), at, gain=0.35 * a, verb=0.4)
    for k in range(30):
        place(bell(rng.uniform(2500, 6000), 0.4), at + rng.uniform(0, 0.8), gain=0.03 * a, pan=rng.uniform(-0.9, 0.9), verb=0.4)


def fx_alarm(a, at, d):
    n = int(d * SR)
    tt = np.arange(n) / SR
    f = np.where(np.floor(tt * 4) % 2 == 0, 880, 660)
    x = np.sign(np.sin(2 * np.pi * np.cumsum(f) / SR))
    place(band(x, 300, 3000) * np.clip(tt / 0.1, 0, 1) * np.clip((d - tt) / 0.2, 0, 1), at, gain=0.035 * a, verb=0.4)


def fx_stamp(a, at):
    place(sweep(170, 48, 0.3) * env_ad(int(0.3 * SR), 0.001, 0.08), at, gain=0.5 * a)
    place(band(noise(int(0.06 * SR)), 1000, 6000) * env_ad(int(0.06 * SR), 0.0005, 0.01), at, gain=0.25 * a)


def fx_slash(a, at):
    n = int(0.35 * SR)
    place(band(noise(n), 2500, 12000) * env_ad(n, 0.02, 0.06), at - 0.02, gain=0.3 * a, pan=-0.3, verb=0.3)
    place(sweep(900, 120, 0.3) * env_ad(int(0.3 * SR), 0.001, 0.1), at, gain=0.2 * a)


def fx_split(a, at):
    for k, nm in enumerate(["A5", "C6", "E6", "G6", "A6"]):
        place(bell(note(nm), 0.9), at + k * 0.07, gain=0.05 * a, pan=-0.6 + 0.3 * k, verb=0.6)


def fx_burst(a, at):
    n = int(0.7 * SR)
    place(band(noise(n), 300, 9000) * env_ad(n, 0.001, 0.2), at, gain=0.25 * a, verb=0.5)


FX = {
    "whoosh": fx_whoosh, "impact": fx_impact, "pop": fx_pop, "ping": fx_ping, "ok": fx_ok, "blip": fx_blip,
    "error": fx_error, "power": fx_power, "crack": fx_crack, "shatter": fx_shatter, "stamp": fx_stamp,
    "slash": fx_slash, "split": fx_split, "burst": fx_burst,
}
FXD = {"riser": fx_riser, "glitch": fx_glitch, "decode": fx_decode, "type": fx_type, "scan": fx_scan, "alarm": fx_alarm}
for q in CUES:
    if q["k"] in FXD:
        FXD[q["k"]](q["a"], q["t"], q["d"])
    else:
        FX[q["k"]](q["a"], q["t"])

# ---------------- music bed (A minor, 120 bpm) ----------------
BEAT = 0.5
CH = {
    "Am": ["A2", "C3", "E3", "A3"], "F": ["F2", "A2", "C3", "F3"], "C": ["C3", "E3", "G3", "C4"],
    "G": ["G2", "B2", "D3", "G3"], "E": ["E2", "G#2", "B2", "E3"], "Dm": ["D3", "F3", "A3", "D4"],
}
ROOT = {"Am": "A1", "F": "F1", "C": "C2", "G": "G1", "E": "E1", "Dm": "D2"}
ARP = {k: [note(n) for n in v[1:]] + [note(v[1]) * 2] for k, v in CH.items()}

# intro drone, rising into the logo hit
dr = pad([note("A1"), note("E2"), note("A2")], 2.6, attack=2.2, release=0.3, bright=4)
place(dr, 0.0, gain=0.22, verb=0.3)


def chord_bed(start, end, prog, bar=2.0, gain=0.11, bright=5):
    b, k = start, 0
    while b < end - 0.05:
        d = min(bar, end - b)
        place(pad([note(n) for n in CH[prog[k % len(prog)]]], d + 0.4, attack=0.25, release=0.5, bright=bright), b, gain=gain, verb=0.35)
        b += bar
        k += 1


# 2.45 – 13.0: hook section, pads + light pulse
chord_bed(2.45, 13.0, ["Am", "F", "C", "G"], bar=2.0, gain=0.10)
b = 4.5
while b < 12.5:
    i = round((b - 4.5) / BEAT)
    if i % 4 == 0:
        place(kick(0.7), b, gain=0.4)
    place(hat(), b + BEAT / 2, gain=0.06, pan=0.3)
    b += BEAT

# 13.0 – 22.0: the problem, darker, driving
chord_bed(13.0, 22.0, ["Am", "Am", "F", "E"], bar=2.0, gain=0.10, bright=4)
b = 13.0
while b < 21.95:
    i = round((b - 13.0) / BEAT)
    place(kick(), b, gain=0.5)
    place(bass(note(ROOT[["Am", "Am", "F", "E"][(i // 4) % 4]]), 0.24), b + BEAT / 2, gain=0.22)
    place(hat(), b + BEAT / 2, gain=0.08, pan=-0.3)
    place(hat(), b + BEAT / 4, gain=0.04, pan=0.3)
    b += BEAT

# 22.0 – 25.3: breakdown, low tension drone
place(pad([note("A1"), note("A#2"), note("E3")], 3.4, attack=0.2, release=0.6, bright=7), 22.0, gain=0.14, verb=0.4)

# 25.3 – 56.0: main groove
PROG = ["Am", "F", "C", "G"]
chord_bed(25.3, 56.0, PROG, bar=2.0, gain=0.09, bright=6)
b = 25.3
while b < 55.9:
    i = round((b - 25.3) / BEAT)
    chord = PROG[(i // 4) % 4]
    place(kick(), b, gain=0.52)
    if i % 2 == 1:
        place(clap(), b, gain=0.28, verb=0.2)
    place(hat(), b, gain=0.05, pan=0.25)
    place(hat(open_=True), b + BEAT / 2, gain=0.07, pan=-0.25)
    place(bass(note(ROOT[chord]), 0.22), b + BEAT / 2, gain=0.2)
    oct_up = 2 if b > 46.4 else 1
    for s in range(4):
        f = ARP[chord][(i * 4 + s) % 4] * 2 * oct_up
        place(pluck(f), b + s * BEAT / 4, gain=0.035, pan=0.5 * np.sin(i + s), verb=0.35)
    b += BEAT

# 56.4 – 63.1: the goal, breakdown with a heartbeat
chord_bed(56.4, 63.1, ["F", "C", "G", "Am"], bar=2.0, gain=0.10, bright=4)
hb = 59.0
while hb < 63.0:
    place(kick(0.8), hb, gain=0.35)
    place(kick(0.6), hb + 0.18, gain=0.22)
    hb += 0.85

# 63.1 – 65.2: build
b, step = 63.1, 0.125
while b < 65.15:
    place(clap(), b, gain=0.08 + 0.2 * (b - 63.1) / 2.1)
    b += step
    if b > 64.2:
        step = 0.0625

# 65.2 – end: outro chord and bells
place(pad([note(n) for n in ["A2", "E3", "A3", "C4", "E4", "B4"]], DUR - 65.2, attack=0.05, release=4.0, bright=7), 65.2, gain=0.24, verb=0.6)
for k, nm in enumerate(["A5", "C6", "E6", "A6", "B6"]):
    place(bell(note(nm), 3.0), 65.3 + k * 0.12, gain=0.06, verb=0.8)
b = 65.2
while b < 69.2:
    place(kick(0.9), b, gain=0.4 * (1 - (b - 65.2) / 4.5))
    b += 1.0

# ---------------- reverb + master ----------------
ir_n = int(2.4 * SR)
ir = noise(ir_n) * np.exp(-np.arange(ir_n) / SR / 0.6)
ir = band(ir, 200, 9000)
ir /= np.sqrt(np.sum(ir ** 2))
size = 1 << int(np.ceil(np.log2(N + ir_n)))
wet = np.fft.irfft(np.fft.rfft(send, size) * np.fft.rfft(ir, size), size)[:N]
L += wet * 0.5
R += wet * 0.5

mix = np.stack([L, R], axis=1)
mix *= (np.clip(t / 0.05, 0, 1) * np.clip((DUR - t) / 1.6, 0, 1))[:, None]
mix = np.tanh(mix * 1.3) / np.tanh(1.3)
mix /= np.max(np.abs(mix)) / 0.89

out = os.path.join(HERE, "genlayer-soundtrack.wav")
with wave.open(out, "wb") as w:
    w.setnchannels(2)
    w.setsampwidth(2)
    w.setframerate(SR)
    w.writeframes((mix * 32767).astype("<i2").tobytes())
print("wrote", out, f"{DUR:.1f}s, {len(CUES)} cues")
