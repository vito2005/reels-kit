#!/usr/bin/env python3
"""Высота голоса на отрезке — кто говорит: ребёнок или взрослый.

    pitch.py <файл> <от> <до> [шаг_мс]        медиана F0 и раскладка по кадрам
    pitch.py scan <файл> <от> <до> [окно_с]   F0 по окнам — видно, где чей голос

Whisper не различает говорящих, а в семейных съёмках это главное: реплика ребёнка
и реплика взрослого в расшифровке выглядят одинаково. F0 их разводит уверенно:
взрослый мужчина 85–150 Гц, взрослая женщина 165–250, ребёнок 2 лет 280–450.

Метод — автокорреляция по кадрам 40 мс с шагом 10 мс на 16 кГц моно, полоса 70–500 Гц.
Кадр считается «озвученным», если пик автокорреляции выше 0.3 от нулевого лага
и энергия выше порога тишины; медиана берётся только по таким кадрам.
"""
import json
import subprocess
import sys

import numpy as np

SR = 16000
FMIN, FMAX = 70.0, 500.0
FRAME = int(0.040 * SR)
HOP = int(0.010 * SR)
VOICED_R = 0.3          # порог пика автокорреляции
SILENCE_DB = -45.0      # ниже — тишина, кадр не считаем


def read_audio(path, start, end):
    """Кусок дорожки как float32 моно 16 кГц."""
    raw = subprocess.run(
        ["ffmpeg", "-v", "error", "-ss", f"{start}", "-to", f"{end}", "-i", path,
         "-vn", "-ac", "1", "-ar", str(SR), "-f", "f32le", "-"],
        capture_output=True, check=True).stdout
    return np.frombuffer(raw, dtype=np.float32)


def f0_frames(x):
    """(времена, F0) по озвученным кадрам — автокорреляция."""
    lag_min, lag_max = int(SR / FMAX), int(SR / FMIN)
    times, f0s = [], []
    for i in range(0, max(0, len(x) - FRAME), HOP):
        fr = x[i:i + FRAME].astype(np.float64)
        rms = np.sqrt(np.mean(fr ** 2)) + 1e-12
        if 20 * np.log10(rms) < SILENCE_DB:
            continue
        fr = fr - fr.mean()
        ac = np.correlate(fr, fr, mode="full")[len(fr) - 1:]
        if ac[0] <= 0:
            continue
        seg = ac[lag_min:lag_max + 1]
        if not len(seg):
            continue
        k = int(np.argmax(seg))
        peak = seg[k] / ac[0]
        if peak < VOICED_R:
            continue
        lag = lag_min + k
        # параболическое уточнение вершины — иначе F0 «квантуется» по лагам
        if 0 < k < len(seg) - 1:
            a, b, c = seg[k - 1], seg[k], seg[k + 1]
            denom = a - 2 * b + c
            if denom:
                lag += 0.5 * (a - c) / denom
        times.append(i / SR)
        f0s.append(SR / lag)
    return np.array(times), np.array(f0s)


def who(f0):
    if f0 is None:
        return "тишина"
    if f0 >= 265:
        return "ребёнок"
    if f0 >= 175:
        return "женщина"
    return "мужчина"


def measure(path, start, end):
    t, f = f0_frames(read_audio(path, start, end))
    if not len(f):
        return dict(n=0, median=None, who="тишина")
    med = float(np.median(f))
    return dict(n=int(len(f)), median=round(med, 1),
                p25=round(float(np.percentile(f, 25)), 1),
                p75=round(float(np.percentile(f, 75)), 1),
                who=who(med))


def main():
    args = sys.argv[1:]
    if args and args[0] == "scan":
        path, start, end = args[1], float(args[2]), float(args[3])
        win = float(args[4]) if len(args) > 4 else 0.5
        t = start
        while t < end:
            hi = min(t + win, end)
            r = measure(path, t, hi)
            bar = "" if r["median"] is None else "#" * int(r["median"] / 25)
            print(f"{t:7.2f}-{hi:<7.2f} {str(r['median'] or '—'):>7} Гц  {r['who']:<8} {bar}")
            t = hi
        return
    path, start, end = args[0], float(args[1]), float(args[2])
    print(json.dumps(measure(path, start, end), ensure_ascii=False))


if __name__ == "__main__":
    main()
