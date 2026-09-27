#!/bin/bash
# Установка на Mac с Apple Silicon (M1–M4). Ставит всё: ~8 ГБ, 20–40 минут в зависимости от интернета.
#   ./install.sh         всё: монтаж и субтитры, поиск звуков, шумодав, замена лица, голос персонажа
#   ./install.sh lite    только основное: ffmpeg, yt-dlp, Whisper (~2 ГБ)
# Можно запускать повторно: что уже стоит, пропускается или обновляется.
set -euo pipefail
cd "$(dirname "$0")"
ROOT=$(pwd)
TOOLS="${REELS_TOOLS:-$HOME/tools}"   # куда ставить FaceFusion и F5-TTS
say() { printf '\n\033[1m▸ %s\033[0m\n' "$*"; }
LITE=0; [ "${1:-}" = lite ] && LITE=1

[ "$(uname -m)" = arm64 ] || echo "Внимание: скрипт рассчитан на Mac с M1–M4, на Intel локальный Whisper не пойдёт."

if ! xcode-select -p >/dev/null 2>&1; then
  say "Command Line Tools (нужны для git и детектора лиц). Согласиться в окне и запустить скрипт ещё раз."
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

say "Python-окружение .venv: Whisper, Pillow, fontTools"
# 3.11: под 3.12 нет готовой сборки шумодава DeepFilterNet
[ -d .venv ] || uv venv --python 3.11 .venv
uv pip install --python .venv/bin/python -q mlx-whisper numpy pillow fonttools

if [ $LITE = 0 ]; then
  say "Поиск звуков (CLAP) и шумодав (DeepFilterNet)"
  uv pip install --python .venv/bin/python -q "torch==2.8.0" "torchaudio==2.8.0" transformers deepfilternet soundfile
  .venv/bin/python -c "
from transformers import ClapModel, ClapProcessor
ClapModel.from_pretrained('laion/clap-htsat-unfused'); ClapProcessor.from_pretrained('laion/clap-htsat-unfused')
print('модель CLAP на месте')" 2>&1 | grep -v Warning || true

  say "Замена лица: FaceFusion → $TOOLS/facefusion"
  mkdir -p "$TOOLS"
  [ -d "$TOOLS/facefusion" ] || git clone --depth 1 https://github.com/facefusion/facefusion "$TOOLS/facefusion"
  cd "$TOOLS/facefusion"
  [ -d .venv ] || uv venv --python 3.12 .venv
  uv pip install --python .venv/bin/python -q pip
  PATH="$PWD/.venv/bin:$PATH" .venv/bin/python install.py default --skip-conda   # install.py берёт pip из PATH
  cd "$ROOT"

  say "Голос персонажа: F5-TTS и Demucs → $TOOLS/f5tts"
  mkdir -p "$TOOLS/f5tts"
  cd "$TOOLS/f5tts"
  [ -d .venv ] || uv venv --python 3.11 .venv
  # torch/torchaudio 2.7.1: с 2.8+ torchaudio требует torchcodec и падает на ffmpeg 7
  uv pip install --python .venv/bin/python -q "torch==2.7.1" "torchaudio==2.7.1" f5-tts demucs huggingface_hub "datasets>=3"   # без datasets>=3 резолвер ставит 2.14, она падает на новом pyarrow
  .venv/bin/python - <<'EOF'
from huggingface_hub import hf_hub_download
from demucs.pretrained import get_model
hf_hub_download("Misha24-10/F5-TTS_RUSSIAN", "F5TTS_v1_Base_v2/model_last_inference.safetensors")
hf_hub_download("Misha24-10/F5-TTS_RUSSIAN", "F5TTS_v1_Base/vocab.txt")
get_model("htdemucs_ft")
print("модели F5-TTS и Demucs на месте")
EOF
  cd "$ROOT"
fi

if ! grep -qs '.local/bin' ~/.zshrc; then
  echo 'export PATH="$HOME/.local/bin:$PATH"' >> ~/.zshrc
  echo "~/.local/bin добавлен в PATH (~/.zshrc) — открыть новый терминал."
fi

say "Готово. Проверка:"
ok() { echo "  ✓ $1"; }; no() { echo "  ✗ $1"; }
[[ "$(ffmpeg -hide_banner -filters 2>/dev/null)" == *"libass"* ]] && ok "ffmpeg с субтитрами" || no "ffmpeg без libass — субтитры не вшить"
~/.local/bin/yt-dlp --version >/dev/null && ok "yt-dlp $(~/.local/bin/yt-dlp --version)"
.venv/bin/python -c "import mlx_whisper" 2>/dev/null && ok "Whisper" || no "Whisper"
if [ $LITE = 0 ]; then
  .venv/bin/python -c "import transformers, torch" 2>/dev/null && ok "поиск звуков" || no "поиск звуков"
  [ -x .venv/bin/deepFilter ] && ok "шумодав" || no "шумодав"
  "$TOOLS/facefusion/.venv/bin/python" -c "import onnxruntime, cv2" 2>/dev/null && ok "FaceFusion (модели скачаются при первой замене)" || no "FaceFusion"
  "$TOOLS/f5tts/.venv/bin/python" -c "import f5_tts, demucs" 2>/dev/null && ok "F5-TTS и Demucs" || no "F5-TTS и Demucs"
fi
