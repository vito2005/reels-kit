"""Синтез фразы голосом персонажа — F5-TTS, русская модель (Misha24-10/F5-TTS_RUSSIAN).

    ~/tools/f5tts/.venv/bin/python tools/voice/f5say.py образец.wav "текст образца" "новая фраза" out.wav [сидов=2]

Образец — 6–10 с чистой речи персонажа (без музыки: сначала Demucs), текст образца дословно.
Ударения ставятся «+» перед гласной: «Я верн+улся». Буквы и аббревиатуры писать по слогам: «Ч+е-Б+э-Д+э» —
слитное «ЧБД» модель ломает. На каждый сид — свой вариант (out-1.wav, out-2.wav …), выбирать на слух.
Ставится `./install.sh voice`.
"""
import sys
from pathlib import Path

import torch
from f5_tts.api import F5TTS
from huggingface_hub import hf_hub_download

REPO = "Misha24-10/F5-TTS_RUSSIAN"   # модель скачивает install.sh, здесь берётся из кэша HuggingFace
ref, ref_text, text, out = sys.argv[1:5]
seeds = int(sys.argv[5]) if len(sys.argv) > 5 else 2
dev = "mps" if torch.backends.mps.is_available() else "cpu"
tts = F5TTS(model="F5TTS_v1_Base", ckpt_file=hf_hub_download(REPO, "F5TTS_v1_Base_v2/model_last_inference.safetensors"),
            vocab_file=hf_hub_download(REPO, "F5TTS_v1_Base/vocab.txt"), device=dev)
out = Path(out)
for seed in range(1, seeds + 1):
    dst = out.with_name(f"{out.stem}-{seed}{out.suffix}")
    tts.infer(ref_file=ref, ref_text=ref_text, gen_text=text, file_wave=str(dst), seed=seed, nfe_step=32,
              remove_silence=False)
    print(dst, flush=True)
