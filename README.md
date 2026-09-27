# reels-kit

Монтаж вертикальных роликов для Reels и Shorts с ИИ-агентом (Codex, Claude Code). Агенту говоришь, что нужно,
а он режет по словам, ставит субтитры, звуки и переходы. Всё на ffmpeg и Whisper, работает локально на Mac с M1–M4.

**Инструкция с примерами:** [docs/index.html](docs/index.html) (локально: `open docs/index.html`).

## Установка

```bash
git clone git@github.com:vito2005/reels-kit.git ~/reels-kit
cd ~/reels-kit && ./install.sh
```

Дополнительно, по желанию: `./install.sh sfx denoise` (поиск звуков, шумодав), `./install.sh face` (замена лица),
`./install.sh voice` (голос персонажа).

## Как работать

Открыть папку в Codex и попросить обычными словами:

> Вот видео ~/Downloads/IMG_1234.MOV. Сделай ролик до 60 секунд: выкинь паузы и повторы, субтитры по словам.

Все команды и правила монтажа агент берёт из [AGENTS.md](AGENTS.md).

## Что внутри

- `tools/edit.py` — расшифровка, нарезка по `cuts.json`, громкость, субтитры, HDR→SDR
- `tools/cards.py`, `assmerge.py` — подписи, время на кадре, склейка субтитров
- `tools/whip.py` — свайп-переходы; `pitch.py` — кто говорит; `sfxtag.py` — поиск звуков
- `tools/face/`, `tools/voice/` — замена лица (FaceFusion) и голос персонажа (F5-TTS)
- `tools/fonts/` — 25 шрифтов с кириллицей; `sfx/` — 159 мем-звуков с каталогом

Код — MIT, шрифты — SIL OFL. Звуки собраны из интернета, лицензии неизвестны.
