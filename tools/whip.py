#!/usr/bin/env python3
"""Свайп-переходы на склейках: whip.py in.mp4 out.mp4 <кадр склейки> [<кадр> …] [--dir left|up|alt] [--frames 6]

Кадр склейки — номер первого кадра нового куска (30 к/с: секунда × 30). На каждой склейке за `frames` кадров
(по умолчанию 6 = 0.2 с, половина до склейки, половина после) картинка уезжает вбок, новый кусок въезжает следом —
как рывок камерой у Mandy Sundberg, только собранный монтажом. Смаз по направлению
движения пропорционален скорости. Длина ролика и точки склеек не меняются — ритм под музыку остаётся.
Звук копируется как есть. Качество — `EDIT_CRF` (по умолчанию 17; мастер для загрузки — 14).
"""
import json
import os
import subprocess
import sys

import numpy as np


def probe(path):
    out = subprocess.run(["ffprobe", "-v", "error", "-select_streams", "v:0", "-show_entries",
                          "stream=width,height,nb_frames", "-of", "json", path], capture_output=True, text=True).stdout
    s = json.loads(out)["streams"][0]
    return s["width"], s["height"]


def box_blur(img, n, axis):
    """Смаз вдоль оси: среднее по окну n пикселей (через кумулятивную сумму)."""
    if n < 2:
        return img
    pad = n // 2
    widths = [(0, 0)] * 3
    widths[axis] = (pad + 1, n - pad - 1)
    p = np.pad(img, widths, mode="edge")
    c = np.cumsum(p, axis=axis, dtype=np.float32)
    hi = np.take(c, range(n, c.shape[axis]), axis=axis)
    lo = np.take(c, range(0, c.shape[axis] - n), axis=axis)
    return (hi - lo) / n


def main():
    args = sys.argv[1:]
    direction, nfr = "left", 6
    if "--dir" in args:
        i = args.index("--dir"); direction = args[i + 1]; del args[i:i + 2]
    if "--frames" in args:
        i = args.index("--frames"); nfr = int(args[i + 1]); del args[i:i + 2]
    src, dst, cuts = args[0], args[1], [int(x) for x in args[2:]]
    w, h = probe(src)
    frames = []
    dec = subprocess.Popen(["ffmpeg", "-v", "error", "-i", src, "-f", "rawvideo", "-pix_fmt", "rgb24", "-"],
                           stdout=subprocess.PIPE)
    size = w * h * 3
    while True:
        buf = dec.stdout.read(size)
        if len(buf) < size:
            break
        frames.append(np.frombuffer(buf, np.uint8).reshape(h, w, 3))
    dec.wait()

    # доля пути 0..1 для кадров перехода: медленный старт, быстрый проход через склейку, мягкая посадка
    half = nfr // 2
    ks = np.arange(-half, nfr - half)                      # относительно кадра склейки
    t = (ks + 0.5) / nfr + 0.5                             # 0..1
    prog = 0.5 - 0.5 * np.cos(np.pi * np.clip(t, 0, 1))    # ease-in-out
    speed = np.gradient(prog)                              # доля кадра за кадр — для смаза
    out = list(frames)
    for n, c in enumerate(cuts):
        d = direction if direction != "alt" else ("left" if n % 2 == 0 else "up")
        axis = 1 if d == "left" else 0
        span = w if axis == 1 else h
        a_last, b_first = frames[c - 1], frames[c]
        for k, p, v in zip(ks, prog, speed):
            f = c + k
            if f < 0 or f >= len(frames):
                continue
            a = frames[f] if k < 0 else a_last            # уходящий кусок
            b = b_first if k < 0 else frames[f]           # входящий
            strip = np.concatenate([a, b], axis=axis)
            off = int(round(p * span))
            view = strip[:, off:off + w] if axis == 1 else strip[off:off + h, :]
            blur = int(v * span * 0.9)
            out[f] = np.clip(box_blur(view.astype(np.float32), blur, axis), 0, 255).astype(np.uint8)

    enc = subprocess.Popen(["ffmpeg", "-v", "error", "-y", "-f", "rawvideo", "-pix_fmt", "rgb24", "-s", f"{w}x{h}",
                            "-r", "30", "-i", "-", "-i", src, "-map", "0:v", "-map", "1:a?", "-c:v", "libx264",
                            "-crf", os.environ.get("EDIT_CRF", "17"), "-preset", "medium", "-pix_fmt", "yuv420p", "-color_primaries", "bt709",
                            "-color_trc", "bt709", "-colorspace", "bt709", "-c:a", "copy", "-movflags", "+faststart", dst],
                           stdin=subprocess.PIPE)
    for f in out:
        enc.stdin.write(f.tobytes())
    enc.stdin.close()
    enc.wait()
    print(f"{dst}: {len(cuts)} свайпов по {nfr} кадров, {direction}")


if __name__ == "__main__":
    main()
