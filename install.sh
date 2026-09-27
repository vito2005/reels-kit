#!/bin/bash
# Установка на Mac с Apple Silicon (M1–M4).
#   ./install.sh            основное: ffmpeg, yt-dlp, Python-окружение .venv, локальный Whisper
#   ./install.sh sfx        + поиск звуков по описанию (CLAP, ~1 ГБ)
#   ./install.sh denoise    + ИИ-шумодав DeepFilterNet
#   ./install.sh face       + замена лица FaceFusion → ~/tools/facefusion (~2 ГБ моделей при первом запуске)
#   ./install.sh voice      + голос персонажа F5-TTS и разделение голоса/музыки Demucs → ~/tools/f5tts (~2 ГБ)
#   ./install.sh all        всё сразу
# Можно запускать повторно: что уже стоит, пропускается.
set -euo pipefail
cd "$(dirname "$0")"
ROOT=$(pwd)
say() { printf '\n\033[1m▸ %s\033[0m\n' "$*"; }

[ "$(uname -m)" = arm64 ] || echo "Внимание: скрипт рассчитан на Mac с M1–M4, на Intel локальный Whisper не пойдёт."

if ! xcode-select -p >/dev/null 2>&1; then
  say "Command Line Tools (нужны для git и детектора лиц). Согласись в окне и запусти скрипт ещё раз."
  xcode-select --install || true
  exit 1
fi

if ! command -v brew >/dev/null; then
  say "Homebrew"
  /bin/bash -c "$(curl -fsSL https://raw.githubusercontent.com/Homebrew/install/HEAD/install.sh)"
  eval "$(/opt/homebrew/bin/brew shellenv)"
fi

say "ffmpeg (с libass для субтитров), uv"
brew list ffmpeg >/dev/null 2>&1 || brew install ffmpeg
command -v uv >/dev/null || brew install uv

say "yt-dlp — скачивать рилсы, Shorts, TikTok"
mkdir -p ~/.local/bin
if [ -x ~/.local/bin/yt-dlp ]; then
  ~/.local/bin/yt-dlp -U || true
else
  curl -fL -o ~/.local/bin/yt-dlp https://github.com/yt-dlp/yt-dlp/releases/latest/download/yt-dlp_macos
  chmod +x ~/.local/bin/yt-dlp
fi

say "Python-окружение .venv (Whisper локально, Pillow, fontTools)"
# 3.11: под 3.12 нет готовой сборки шумодава DeepFilterNet
[ -d .venv ] || uv venv --python 3.11 .venv
uv pip install --python .venv/bin/python -q mlx-whisper numpy pillow fonttools

want() { for a in "${ARGS[@]}"; do [ "$a" = "$1" ] || [ "$a" = all ] && return 0; done; return 1; }
ARGS=("${@:-}")

if want sfx; then
  say "Поиск звуков (CLAP)"
  uv pip install --python .venv/bin/python -q torch transformers
fi

if want denoise; then
  say "Шумодав DeepFilterNet"
  uv pip install --python .venv/bin/python -q deepfilternet "torch==2.8.0" "torchaudio==2.8.0" soundfile
fi

if want face; then
  say "FaceFusion → ~/tools/facefusion"
  mkdir -p ~/tools
  [ -d ~/tools/facefusion ] || git clone --depth 1 https://github.com/facefusion/facefusion ~/tools/facefusion
  cd ~/tools/facefusion
  [ -d .venv ] || uv venv --python 3.12 .venv
  uv pip install --python .venv/bin/python -q pip
  PATH="$PWD/.venv/bin:$PATH" .venv/bin/python install.py default --skip-conda   # install.py берёт pip из PATH
  cd "$ROOT"
fi

if want voice; then
  say "F5-TTS + Demucs → ~/tools/f5tts"
  mkdir -p ~/tools/f5tts/ckpt
  cd ~/tools/f5tts
  [ -d .venv ] || uv venv --python 3.11 .venv
  # torch/torchaudio 2.7.1: с 2.8+ torchaudio требует torchcodec и падает на ffmpeg 7
  uv pip install --python .venv/bin/python -q "torch==2.7.1" "torchaudio==2.7.1" f5-tts demucs huggingface_hub
  .venv/bin/python - <<'EOF'
from huggingface_hub import hf_hub_download
import shutil
m = hf_hub_download("Misha24-10/F5-TTS_RUSSIAN", "F5TTS_v1_Base_v2/model_last_inference.safetensors")
v = hf_hub_download("Misha24-10/F5-TTS_RUSSIAN", "F5TTS_v1_Base/vocab.txt")
shutil.copy(m, "ckpt/model_last_inference.safetensors"); shutil.copy(v, "ckpt/vocab.txt")
print("модель F5-TTS на месте")
EOF
  cd "$ROOT"
fi

if ! grep -qs '.local/bin' ~/.zshrc; then
  echo 'export PATH="$HOME/.local/bin:$PATH"' >> ~/.zshrc
  echo "~/.local/bin добавлен в PATH (~/.zshrc) — открой новый терминал."
fi

say "Готово. Проверка:"
[[ "$(ffmpeg -hide_banner -filters 2>/dev/null)" == *"libass"* ]] && echo "  ffmpeg: субтитры ок" || echo "  ffmpeg: НЕТ libass — субтитры не вшить"
.venv/bin/python -c "import mlx_whisper" && echo "  Whisper: ок"
~/.local/bin/yt-dlp --version | sed 's/^/  yt-dlp: /'
