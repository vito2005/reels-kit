#!/usr/bin/env python3
"""Библиотека звуков: разметка и поиск по смыслу (CLAP — модель «звук ↔ текст», локально).

  python3 tools/sfxtag.py index sfx/                 # эмбеддинги всех звуков → sfx/index.npz + sfx/tags.json
  python3 tools/sfxtag.py search sfx/ "падение, провал" [10]   # найти звук по описанию (по-английски точнее)

Модель laion/clap-htsat-unfused (~600 МБ, кэш HuggingFace). Метки в tags.json — топ-3 из LABELS,
это подсказка, а не истина: слушать всё равно ушами.
"""
import json, os, subprocess, sys
import numpy as np

MODEL = "laion/clap-htsat-unfused"
EXT = (".mp3", ".wav", ".m4a", ".aac", ".ogg", ".flac")
LABELS = [
    "whoosh transition", "swoosh fast", "riser build-up", "reverse cymbal", "impact boom hit",
    "bass drop", "punch hit", "slap", "cartoon boing", "cartoon slide whistle", "cartoon running feet",
    "fail trombone wah wah", "sad violin", "error buzzer wrong answer", "correct answer ding chime",
    "bell ding", "camera shutter", "mouse click", "record scratch", "tape rewind",
    "drum roll", "rimshot ba dum tss", "dramatic dun dun dun", "suspense tension music", "heartbeat",
    "crowd laughing", "kids laughing", "crowd cheering", "kids cheering hooray", "crowd booing",
    "crowd wow", "crowd aww", "applause clapping", "man screaming", "sneeze", "fart", "quack duck",
    "rubber squeak toy", "glass breaking", "explosion", "car horn", "air horn", "phone ringing",
    "alarm clock", "door knock", "door bell", "school bell", "spaceship fly by", "rocket launch",
    "plane flyover", "splat", "bottle cork pop", "video game jump", "video game death", "8-bit music",
    "funny cartoon music", "whimsical ukulele music", "choir hallelujah", "christmas music",
    "romantic sad piano", "mysterious spooky music", "speech voice", "shout exclamation",
]


def load(path, sr=48000):
    raw = subprocess.run(["ffmpeg", "-v", "error", "-i", path, "-t", "10", "-ac", "1", "-ar", str(sr),
                          "-f", "f32le", "-"], capture_output=True, check=True).stdout
    return np.frombuffer(raw, np.float32)


def model():
    from transformers import ClapModel, ClapProcessor
    return ClapModel.from_pretrained(MODEL).eval(), ClapProcessor.from_pretrained(MODEL)


def feats(out):
    """transformers 5 отдаёт объект с pooler_output вместо тензора."""
    return getattr(out, "pooler_output", out)


def text_emb(m, p, texts):
    import torch
    with torch.no_grad():
        e = m.get_text_features(**p(text=texts, return_tensors="pt", padding=True))
    e = feats(e).numpy()
    return e / np.linalg.norm(e, axis=1, keepdims=True)


def index(root):
    import torch
    m, p = model()
    files = sorted(os.path.relpath(os.path.join(d, f), root) for d, _, fs in os.walk(root)
                   for f in fs if f.lower().endswith(EXT) and "FULL" not in f.upper())
    embs = []
    for f in files:
        a = load(os.path.join(root, f))
        with torch.no_grad():
            e = feats(m.get_audio_features(**p(audios=[a], sampling_rate=48000, return_tensors="pt"))).numpy()[0]
        embs.append(e / np.linalg.norm(e))
    embs = np.array(embs)
    np.savez(os.path.join(root, "index.npz"), files=np.array(files), embs=embs)
    sims = embs @ text_emb(m, p, LABELS).T
    tags = {f: [[LABELS[j], round(float(sims[i, j]), 3)] for j in np.argsort(-sims[i])[:3]]
            for i, f in enumerate(files)}
    json.dump(tags, open(os.path.join(root, "tags.json"), "w"), ensure_ascii=False, indent=1)
    for f, t in tags.items():
        print(f"{f[-44:]:44}  " + " | ".join(x[0] for x in t))


def search(root, query, k=10):
    d = np.load(os.path.join(root, "index.npz"))
    m, p = model()
    s = d["embs"] @ text_emb(m, p, [query])[0]
    for i in np.argsort(-s)[:k]:
        print(f"{s[i]:.3f}  {d['files'][i]}")


if __name__ == "__main__":
    cmd, root = sys.argv[1], sys.argv[2]
    if cmd == "index":
        index(root)
    else:
        search(root, sys.argv[3], int(sys.argv[4]) if len(sys.argv) > 4 else 10)
