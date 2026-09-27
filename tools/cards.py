#!/usr/bin/env python3
"""Карточки-подписи (без пословной подсветки) для роликов-списков: cards.py cards.json out.ass

cards.json:
  {"size": [1080, 1920], "margin_v": 560,
   "cards": [[0.0, 2.6, "Поезд с младенцем.|Чего не пишут в отзывах", "box"],
             [2.6, 5.2, "Купе два на два —|теперь это вся квартира"],
             {"at": [2.6, 3.5], "text": "март 2025 · 7 месяцев", "style": "top"},
             {"at": [2.6, 3.5], "text": "40", "style": "num"}]}

«|» — перенос строки. Стили:
  без стиля  белый текст с тёмной обводкой внизу кадра, как обычные субтитры;
  "box"      белый на терракотовой плашке — интро и финал;
  "top"      мелкая строка сверху (дата, возраст) — `top_mv` px от верха, по умолчанию 400;
  "num"      крупное жёлтое число сверху (счётчик) — `num_mv` px от верха, по умолчанию 150;
  "clock"    время дня по центру кадра тонкой антиквой с мягкой тенью (размытый слой ниже), без обводки и без фейда —
             «день по часам» (как у Mandy Sundberg). Шрифт `clock_font` (Didot),
             кегль `clock_px` (86), высота `clock_y` (px от верха; по умолчанию центр кадра).
Размеры: `size_px` (обычные карточки), `top_px`, `num_px`. Шрифт — `font` (по умолчанию Futura,
у "top"/"num" — `num_font`, по умолчанию Alumni Black, как в кинетических субтитрах).
Куски-карточки можно задавать списком [от, до, текст, стиль] или объектом {"at": [от, до], …}.
"""
import json
import sys
from pathlib import Path

ACCENT = "&H002AD2F5"    # жёлтый, как подсветка слова в стиле «e»/«f»
BOX = "&H003A60B9"       # терракота

HEADER = """[Script Info]
ScriptType: v4.00+
PlayResX: {w}
PlayResY: {h}
WrapStyle: 0
ScaledBorderAndShadow: yes

[V4+ Styles]
Format: Name, Fontname, Fontsize, PrimaryColour, SecondaryColour, OutlineColour, BackColour, Bold, Italic, Underline, StrikeOut, ScaleX, ScaleY, Spacing, Angle, BorderStyle, Outline, Shadow, Alignment, MarginL, MarginR, MarginV, Encoding
Style: Card,{font},{size},&H00FFFFFF,&H000000FF,&H00101010,&H90000000,1,0,0,0,100,100,1,0,1,{outline},{shadow},2,{mlr},{mlr},{mv},204
Style: CardBox,{font},{size},&H00FFFFFF,&H000000FF,{box_c},{box_c},1,0,0,0,100,100,1,0,3,{box},0,2,{mlr},{mlr},{mv},204
Style: CardTop,{num_font},{top_size},&H00FFFFFF,&H000000FF,&H00101010,&H90000000,0,0,0,0,100,100,2,0,1,{outline},{shadow},8,{mlr},{mlr},{top_mv},204
Style: CardClock,{clock_font},{clock_size},&H00FFFFFF,&H000000FF,&H00000000,&H80000000,0,0,0,0,100,100,2,0,1,0,{clock_shadow},5,{mlr},{mlr},0,204
Style: CardNum,{num_font},{num_size},{accent},&H000000FF,&H00101010,&HA0000000,0,0,0,0,100,100,0,0,1,{num_outline},{num_shadow},8,{mlr},{mlr},{num_mv},204

[Events]
Format: Layer, Start, End, Style, Name, MarginL, MarginR, Effect, Text
"""

STYLE_NAME = {"box": "CardBox", "top": "CardTop", "num": "CardNum", "clock": "CardClock"}


def t(sec):
    h, r = divmod(max(sec, 0), 3600)
    m, s = divmod(r, 60)
    return f"{int(h):d}:{int(m):02d}:{s:05.2f}"


def fields(card):
    """Карточка — список [от, до, текст, стиль?] или объект {"at": [от, до], "text", "style", "px"}.

    "px" — свой кегль вместо стилевого (например, у карточки-разгадки посреди ролика)."""
    if isinstance(card, dict):
        a, b = card["at"]
        return a, b, card["text"], card.get("style", ""), card.get("px")
    a, b, text = card[0], card[1], card[2]
    return a, b, text, (card[3] if len(card) > 3 else ""), None


def main(src, out):
    d = json.load(open(src))
    w, h = d.get("size", [1080, 1920])
    k = w / 1080
    head = HEADER.format(
        w=w, h=h, font=d.get("font", "Futura"), num_font=d.get("num_font", "Alumni Black"),
        size=round(d.get("size_px", 82) * k), top_size=round(d.get("top_px", 52) * k),
        num_size=round(d.get("num_px", 210) * k),
        clock_font=d.get("clock_font", "Didot"), clock_size=round(d.get("clock_px", 86) * k), clock_shadow=0, accent=ACCENT, box_c=BOX,
        outline=round(5 * k), num_outline=round(10 * k), num_shadow=round(6 * k), shadow=round(3 * k), box=round(14 * k),
        mlr=round(120 * k), mv=round(d.get("margin_v", 560) * k),
        top_mv=round(d.get("top_mv", 400) * k), num_mv=round(d.get("num_mv", 150) * k))
    events = []
    for card in d["cards"]:
        a, b, text, style, px = fields(card)
        fade = 0 if style == "clock" else d.get("fade", 120)
        size = f"\\fs{round(px * k)}" if px else ""
        if style == "clock" and d.get("clock_y"):   # своя высота вместо центра кадра (px от верха при 1920)
            size += f"\\pos({w // 2},{round(d['clock_y'] * k)})"
        if style == "clock":   # мягкая тень — размытая тёмная копия слоем ниже, иначе цифры тонут на светлом
            events.append(f"Dialogue: 0,{t(a)},{t(b)},CardClock,,0,0,,{{\\shad0\\1c&H000000&\\1a&H70&\\blur{round(10 * k)}{size}}}"
                          + text.replace("|", "\\N"))
        events.append(f"Dialogue: 1,{t(a)},{t(b)},{STYLE_NAME.get(style, 'Card')},,0,0,,"
                      + (f"{{\\fad({fade},{fade}){size}}}" if fade else f"{{{size}}}" if size else "") + text.replace("|", "\\N"))
    Path(out).write_text(head + "\n".join(events) + "\n")
    print(f"{len(events)} карточек → {out}")
    for card in d["cards"]:
        a, b, text, style, px = fields(card)
        print(f"  {a:5.1f}–{b:4.1f} {style or '—':>4}  {text.replace('|', ' / ')}")


main(sys.argv[1], sys.argv[2])
