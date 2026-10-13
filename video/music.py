"""Synthesize the explainer soundtrack (no external assets).

Event times are authored on the composition's 67 s grid and stretched by SPEED,
matching SPEED / GATE_LEN / END in index.html.

usage: python3 music.py <out.wav>
"""
import sys
import wave

import numpy as np

SPEED, GATE_LEN, END = 1.3, 7.0, 67.0
SR = 48000
D = END * SPEED
N = int(SR * D)
rng = np.random.default_rng(7)
L = np.zeros(N)
R = np.zeros(N)


def at(t: float) -> float:
    """Map a time on the original 60 s grid (before the gate scene) to output seconds."""
    return (t if t < 36 else t + GATE_LEN) * SPEED


def hz(m: float) -> float:
    return 440 * 2 ** ((m - 69) / 12)


def env(n: int, a: float, r: float) -> np.ndarray:
    e = np.ones(n)
    ai, ri = int(a * SR), int(r * SR)
    e[:ai] = np.linspace(0, 1, ai)
    e[-ri:] *= np.linspace(1, 0, ri)
    return e


def add(sig: np.ndarray, start: float, pan: float = 0.0, g: float = 1.0) -> None:
    i = int(start * SR)
    if i >= N:
        return
    j = min(N, i + len(sig))
    s = sig[: j - i] * g
    L[i:j] += s * np.sqrt((1 - pan) / 2)
    R[i:j] += s * np.sqrt((1 + pan) / 2)


BEAT = 0.6 * SPEED
CD = 8 * BEAT  # two bars per chord
CH = [[45, 57, 60, 64, 67, 71], [41, 57, 60, 64, 65, 69], [48, 55, 59, 64, 67, 72], [47, 55, 59, 62, 64, 67]]

# pad + bass
s, k = 0.0, 0
while s < D:
    ch = CH[k % 4]
    n = int(CD * SR) + int(1.2 * SR)
    tt = np.arange(n) / SR
    sig = np.zeros(n)
    for m in ch[1:]:
        for det in (-0.08, 0.08):
            f = hz(m) * 2 ** (det / 12)
            for h in range(1, 6):
                sig += np.sin(2 * np.pi * f * h * tt + h) * (0.5 / h ** 1.6)
    sig *= env(n, 1.0, 1.4) * 0.018
    add(sig, s, -0.2)
    add(sig, s + 0.011, 0.25)
    add(np.sin(2 * np.pi * hz(ch[0]) * tt) * env(n, 0.05, 1.0) * 0.10, s)
    s += CD
    k += 1

# arpeggio
i, s = 0, at(9.6)
while s < at(57.0):
    ch = CH[int(s // CD) % 4]
    m = ch[1:][[0, 2, 4, 1, 3, 5, 2, 4][i % 8] % (len(ch) - 1)] + 12
    tt = np.arange(int(0.5 * SR)) / SR
    f = hz(m)
    sig = (np.sin(2 * np.pi * f * tt) + 0.35 * np.sin(4 * np.pi * f * tt) + 0.1 * np.sin(6 * np.pi * f * tt)) * np.exp(-tt * 9)
    g = 0.045 * min(1, (s - at(9.6)) / 3) * (1.15 if at(47) < s < at(54.5) else 1)
    add(sig, s, [-0.5, 0.5][i % 2], g)
    i += 1
    s += BEAT / 2


def kick() -> np.ndarray:
    tt = np.arange(int(0.35 * SR)) / SR
    f = 50 + 90 * np.exp(-tt * 30)
    return np.sin(2 * np.pi * np.cumsum(f) / SR) * np.exp(-tt * 9)


def hat() -> np.ndarray:
    n = int(0.06 * SR)
    x = np.diff(np.concatenate([[0], rng.standard_normal(n)]))
    return x * np.exp(-np.arange(n) / SR * 70)


b = at(18.0)
while b < at(54.5):
    add(kick(), b, 0, 0.22)
    if b >= at(28):
        add(hat(), b + BEAT / 2, 0.3, 0.035)
    b += BEAT


def whoosh(d: float = 0.8) -> np.ndarray:
    n = int(d * SR)
    x = np.convolve(rng.standard_normal(n), np.ones(40) / 40, "same")
    return x * np.sin(np.linspace(0, np.pi, n)) ** 2


def click() -> np.ndarray:
    tt = np.arange(int(0.03 * SR)) / SR
    return (rng.standard_normal(len(tt)) * 0.5 + np.sin(2 * np.pi * 2500 * tt)) * np.exp(-tt * 250)


for t in (9.3, 17.8, 27.8, 35.8, 54.3, 57.2):
    add(whoosh(), at(t) - 0.4, 0, 0.10)
add(whoosh(), (36 + GATE_LEN - 0.2) * SPEED - 0.4, 0, 0.10)  # gate -> panel
add(whoosh(), 46.8 * SPEED + GATE_LEN * SPEED - 0.4, 0, 0.10)  # panel -> results
for t in (40.4, 43.3):
    add(click(), at(t), 0, 0.25)
# gate verdicts
add(click(), (39.7) * SPEED, 0, 0.18)
add(click(), (40.2) * SPEED, 0, 0.18)
# typing ticks: typing has a fixed duration in every language (see typed() in index.html)
for start, dur, ticks in ((1.0, 1.6, 30), (18.8, 1.47, 30), (58.4, 0.77, 20)):
    for c in range(ticks):
        add(click(), at(start + c / ticks * dur), -0.2 if c % 2 else 0.2, 0.035)

mix = np.stack([L, R], 1)
fade = np.ones(N)
fi, fo = int(0.8 * SR), int(2.0 * SR)
fade[:fi] = np.linspace(0, 1, fi)
fade[-fo:] = np.linspace(1, 0, fo) ** 1.5
mix = np.tanh(mix * fade[:, None] * 1.2)
mix /= np.abs(mix).max() / 0.89
with wave.open(sys.argv[1], "wb") as w:
    w.setnchannels(2)
    w.setsampwidth(2)
    w.setframerate(SR)
    w.writeframes((mix * 32767).astype("<i2").tobytes())
print(f"soundtrack: {D:.1f}s -> {sys.argv[1]}")
