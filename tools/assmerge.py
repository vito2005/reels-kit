#!/usr/bin/env python3
"""Склеить несколько .ass в один: assmerge.py out.ass a.ass b.ass ...

Нужно, когда на ролике и пословные субтитры (`edit.py captions`), и карточки
(`cards.py`): вшивать два файла по очереди — это два прохода кодирования и лишняя
потеря качества. Здесь берётся шапка первого файла, стили всех (по имени, первый
побеждает) и события всех подряд — libass сам разложит их по времени.

Файлы должны быть в одном разрешении (PlayResX/Y) — иначе кегли поедут; при
расхождении скрипт ругается и ничего не пишет.
"""
import re
import sys
from pathlib import Path


def parse(text):
    head, styles, events = [], [], []
    section = None
    for line in text.splitlines():
        low = line.strip().lower()
        if low.startswith("[") and low.endswith("]"):
            section = low
            if section != "[events]":
                head.append(line)
            continue
        if section == "[events]":
            if line.startswith("Format:"):
                head_events = line
                continue
            if line.strip():
                events.append(line)
        else:
            if line.startswith("Style:"):
                styles.append(line)
            else:
                head.append(line)
    return head, styles, events


def playres(text):
    x = re.search(r"PlayResX:\s*(\d+)", text)
    y = re.search(r"PlayResY:\s*(\d+)", text)
    return (x.group(1) if x else None, y.group(1) if y else None)


def main(out, paths):
    texts = [Path(p).read_text() for p in paths]
    res = {playres(t) for t in texts}
    if len(res) > 1:
        sys.exit(f"разное разрешение у файлов: {res} — субтитры не склеить")
    head, styles, events = parse(texts[0])
    seen = {re.match(r"Style:\s*([^,]+)", s).group(1).strip() for s in styles}
    for t in texts[1:]:
        _, st, ev = parse(t)
        for s in st:
            name = re.match(r"Style:\s*([^,]+)", s).group(1).strip()
            if name not in seen:
                seen.add(name)
                styles.append(s)
        events += ev
    body = "\n".join(head).rstrip() + "\n" + "\n".join(styles) + "\n\n[Events]\n" \
        + "Format: Layer, Start, End, Style, Name, MarginL, MarginR, Effect, Text\n" \
        + "\n".join(events) + "\n"
    Path(out).write_text(body)
    print(f"{len(styles)} стилей, {len(events)} событий → {out}")


main(sys.argv[1], sys.argv[2:])
