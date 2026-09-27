"""Сглаживание замены лица во времени: out = до + сглаженная(после − до) внутри планов.

Движение берётся из «до» как есть, а слой замены (то, что FaceFusion наложил поверх) усредняется
по соседним кадрам — дрожание маски и бровей гасится. Между планами не сглаживается.

    deflicker.py before.mp4 after.mp4 out.mp4 "20.33-24.54,27.29-43.88" [5] [9]
Второе окно — для верхних 45 % лица (лоб, брови): там мелькание заметнее, а губ нет, двоиться нечему.
Запускать питоном FaceFusion: ~/tools/facefusion/.venv/bin/python (там cv2 и numpy).
"""
import subprocess
import sys

import cv2
import numpy as np

before, after, out, spans = sys.argv[1], sys.argv[2], sys.argv[3], sys.argv[4]
win = int(sys.argv[5]) if len(sys.argv) > 5 else 5
win_top = int(sys.argv[6]) if len(sys.argv) > 6 else win
def tri(n):
    return [min(k + 1, n - k) for k in range(n)]
weights, weights_top = tri(win), tri(win_top)
TOP = 0.45

cb, ca = cv2.VideoCapture(before), cv2.VideoCapture(after)
fps = ca.get(cv2.CAP_PROP_FPS)
w, h = int(ca.get(cv2.CAP_PROP_FRAME_WIDTH)), int(ca.get(cv2.CAP_PROP_FRAME_HEIGHT))
n = int(ca.get(cv2.CAP_PROP_FRAME_COUNT))
ranges = [tuple(round(float(x) * fps) for x in s.split("-")) for s in spans.split(",")]
shot_of = {}
for k, (a, b) in enumerate(ranges):
    for i in range(a, b):
        shot_of[i] = k

enc = subprocess.Popen(["ffmpeg", "-v", "error", "-y", "-f", "rawvideo", "-pix_fmt", "bgr24", "-s", f"{w}x{h}",
                        "-r", str(fps), "-i", "-", "-i", after, "-map", "0:v", "-map", "1:a?", "-c:v", "libx264",
                        "-crf", "14", "-preset", "fast", "-pix_fmt", "yuv420p", "-c:a", "copy", out],
                       stdin=subprocess.PIPE)

jitter_before, jitter_after = [], []
i = 0
while i < n:
    if i not in shot_of:
        ok, fa = ca.read()
        cb.read()
        if not ok:
            break
        enc.stdin.write(fa.tobytes())
        i += 1
        continue
    a, b = ranges[shot_of[i]]
    # план потоком: окно из win кадров слоя замены, сглаженный кадр выдаётся с задержкой r
    r = max(win, win_top) // 2
    base, delta = {}, {}
    prev = None
    t_out = a
    for t in range(a, b + r):
        if t < b:
            okb, fb = cb.read()
            oka, fa = ca.read()
            if okb and oka:
                base[t] = fb
                delta[t] = fa.astype(np.int16) - fb.astype(np.int16)
        c = t - r
        if c < a or c not in delta:
            continue
        def smooth(ws):
            acc = np.zeros(delta[c].shape, dtype=np.float32)
            wsum = 0.0
            for j, wt in enumerate(ws):
                s_ = c + j - len(ws) // 2
                if s_ in delta:
                    acc += wt * delta[s_]
                    wsum += wt
            return acc / wsum
        sm = smooth(weights)
        rows = np.where((np.abs(delta[c]).sum(axis=2) > 12).any(axis=1))[0]
        if win_top != win and len(rows):
            y0, y1 = rows[0], rows[-1]
            cut, feather = y0 + TOP * (y1 - y0), 0.1 * (y1 - y0) + 1
            alpha = np.clip((cut + feather - np.arange(sm.shape[0])) / feather, 0, 1)[:, None, None]
            sm = sm * (1 - alpha) + smooth(weights_top) * alpha
        enc.stdin.write(np.clip(base[c].astype(np.float32) + sm, 0, 255).astype(np.uint8).tobytes())
        if c - 1 in delta:   # дрожание слоя замены там, где замена есть
            mask = np.abs(delta[c]).sum(axis=2) > 12
            if mask.any():
                jitter_before.append(np.abs(delta[c] - delta[c - 1])[mask].mean())
                jitter_after.append(np.abs(sm - prev)[mask].mean())
        prev = sm
        for old in [k for k in delta if k < c - r]:
            del delta[old], base[old]
        t_out = c + 1
    i = t_out

enc.stdin.close()
enc.wait()
print(f"дрожание слоя замены: было {np.mean(jitter_before):.2f}, стало {np.mean(jitter_after):.2f}; "
      f"худший кадр было {np.max(jitter_before):.2f}, стало {np.max(jitter_after):.2f}")
