#!/usr/bin/env python3
"""Мягкое размытие, которое едет по ключевым точкам: закрыть лишнее в кадре (номер машины, чужое лицо, экран телефона,
то, что не для публикации).

    blurtrack.py check <видео> spec.json out.jpg   # кадры в ключевые моменты с контуром пятна — сверить до рендера
    blurtrack.py render <видео> spec.json out.mp4   # размыть (звук копируется)

spec.json:
    {"coords": "px",                        # "px" — пиксели показанного кадра (после поворота), "frac" — доли 0…1
     "regions": [
       {"shape": "ellipse",                 # "ellipse" (по умолчанию, мягкий край) или "rect" (скруглённый прямоугольник)
        "w": 120, "h": 170,                 # размер пятна (в тех же единицах, что coords); на протяжении пятна постоянный
        "blur": 18,                         # сила размытия (радиус boxblur, px); 30+ — от предмета остаётся только цвет
        "feather": 3,                       # мягкость края: 1 — очень мягкий, 6 — почти резкий
        "keys": [[61.7, 100, 797], [62.0, 102, 850], [62.4, 99, 860]],   # [секунда, cx, cy] — центр пятна
        "from": 61.7, "to": 65.0}]}         # когда пятно есть (по умолчанию — от первой до последней точки)

Между точками центр едет линейно; раньше первой и позже последней точки пятно стоит на месте. Точки ставить через
0.2–0.3 с там, где предмет двигается, реже — где стоит; сверять `check`. Время — секунды ЭТОГО видео.
Для лиц точки даёт детектор: `edit.py facetrack видео 12 18 0.2` печатает [[сек, cx, cy], …] в долях — это готовые "keys"
при "coords": "frac" (размер пятна тогда тоже в долях, например "w": 0.3, "h": 0.25).
Размывать лучше готовый рендер (до `burn`, чтобы субтитры остались резкими) или кусок исходника, вырезанный окном.
HDR-исходник (HLG/PQ с айфона) пишется обратно в 10 бит HEVC с теми же тегами — `render` edit.py потом сам сведёт в SDR.
"""
import json
import subprocess
import sys
from pathlib import Path

from PIL import Image, ImageDraw, ImageFont

FONT = Path(__file__).with_name("fonts") / "Oswald-Bold.ttf"


def probe(src):
    out = subprocess.run(["ffprobe", "-v", "error", "-select_streams", "v:0", "-show_entries",
                          "stream=width,height,color_transfer,color_primaries,color_space:stream_side_data=rotation",
                          "-of", "json", src], capture_output=True, text=True, check=True).stdout
    s = json.loads(out)["streams"][0]
    w, h = s["width"], s["height"]
    rot = next((abs(int(d.get("rotation", 0))) for d in s.get("side_data_list", []) if "rotation" in d), 0)
    if rot in (90, 270):
        w, h = h, w
    hdr = s.get("color_transfer") in ("arib-std-b67", "smpte2084")
    return w, h, hdr, s


def load(spec_path, W, H):
    spec = json.load(open(spec_path))
    frac = spec.get("coords", "px") == "frac"
    regs = []
    for r in spec["regions"]:
        sx, sy = (W, H) if frac else (1, 1)
        keys = sorted([float(t), float(x) * sx, float(y) * sy] for t, x, y in r["keys"])
        w, h = max(2, round(r["w"] * sx)) // 2 * 2, max(2, round(r["h"] * sy)) // 2 * 2
        regs.append(dict(shape=r.get("shape", "ellipse"), w=w, h=h, blur=r.get("blur", 18), feather=r.get("feather", 3),
                         keys=keys, t0=float(r.get("from", keys[0][0])), t1=float(r.get("to", keys[-1][0]))))
    return regs


def pos(keys, t):
    """Центр пятна в момент t — линейно между точками."""
    if t <= keys[0][0]:
        return keys[0][1:]
    for (a, xa, ya), (b, xb, yb) in zip(keys, keys[1:]):
        if t <= b:
            k = (t - a) / (b - a) if b > a else 1
            return [xa + (xb - xa) * k, ya + (yb - ya) * k]
    return keys[-1][1:]


def expr(keys, i):
    """То же для ffmpeg: кусочно-линейная функция от t (i = 1 → x, 2 → y)."""
    e = f"{keys[-1][i]:.1f}"
    for (a, *pa), (b, *pb) in reversed(list(zip(keys, keys[1:]))):
        if b <= a:
            continue
        e = f"if(lt(t,{b:.3f}),{pa[i-1]:.1f}+({pb[i-1] - pa[i-1]:.1f})*(t-{a:.3f})/{b - a:.3f},{e})"
    return f"if(lt(t,{keys[0][0]:.3f}),{keys[0][i]:.1f},{e})"


def check(src, spec_path, out):
    W, H, _, _ = probe(src)
    regs = load(spec_path, W, H)
    times = sorted({round(k[0], 2) for r in regs for k in r["keys"]})
    if len(times) > 24:                                    # не больше 24 кадров в листе
        times = times[::-(-len(times) // 24)]
    tiles = []
    for t in times:
        raw = subprocess.run(["ffmpeg", "-v", "error", "-ss", str(t), "-i", src, "-frames:v", "1", "-f", "rawvideo",
                              "-pix_fmt", "rgb24", "-"], capture_output=True, check=True).stdout
        im = Image.frombytes("RGB", (W, H), raw[:W * H * 3]); d = ImageDraw.Draw(im)
        for r in regs:
            if r["t0"] - 1e-3 <= t <= r["t1"] + 1e-3:
                cx, cy = pos(r["keys"], t); box = (cx - r["w"] / 2, cy - r["h"] / 2, cx + r["w"] / 2, cy + r["h"] / 2)
                (d.ellipse if r["shape"] == "ellipse" else d.rectangle)(box, outline=(255, 40, 40), width=max(3, W // 300))
        fs = max(24, W // 14)
        font = ImageFont.truetype(str(FONT), fs) if FONT.exists() else ImageFont.load_default()
        d.rectangle((0, 0, fs * 3, int(fs * 1.4)), fill=(0, 0, 0)); d.text((fs // 4, 0), f"{t:.2f}", font=font, fill=(255, 230, 0))
        tiles.append(im.resize((360, round(360 * H / W))))
    cols = min(6, len(tiles)); rows = -(-len(tiles) // cols)
    sheet = Image.new("RGB", (cols * 360, rows * tiles[0].height))
    for i, im in enumerate(tiles):
        sheet.paste(im, ((i % cols) * 360, (i // cols) * im.height))
    sheet.save(out, quality=88)
    print(out)


def render(src, spec_path, out):
    W, H, hdr, s = probe(src)
    regs = load(spec_path, W, H)
    fmt = "yuva444p10le" if hdr else "yuva444p"
    parts, last = [], "0:v"
    for i, r in enumerate(regs):
        w, h = r["w"], r["h"]
        X = f"({expr(r['keys'], 1)})-{w // 2}"
        Y = f"({expr(r['keys'], 2)})-{h // 2}"
        f = r["feather"]
        if r["shape"] == "ellipse":
            mask = f"255*clip((1-(pow((X-{w / 2})/{w / 2},2)+pow((Y-{h / 2})/{h / 2},2)))*{f},0,1)"
        else:   # прямоугольник с мягким краем шириной 1/(2·feather) от меньшей стороны
            e = min(w, h) / (2 * f)
            mask = f"255*clip(min(min(X,{w}-X),min(Y,{h}-Y))/{e:.1f},0,1)"
        if hdr:
            mask = mask.replace("255*", "1023*")
        parts.append(f"[{last}]split[a{i}][b{i}];[b{i}]crop=w={w}:h={h}:x='{X}':y='{Y}',boxblur={r['blur']}:2,format={fmt},"
                     f"geq=lum='lum(X,Y)':cb='cb(X,Y)':cr='cr(X,Y)':a='{mask}'[m{i}];"
                     f"[a{i}][m{i}]overlay=x='{X}':y='{Y}':enable='between(t,{r['t0']:.3f},{r['t1']:.3f})'[v{i}]")
        last = f"v{i}"
    fc = ";".join(parts) + f";[{last}]format={'yuv420p10le' if hdr else 'yuv420p'}[v]"
    if hdr:   # 10 бит HEVC с исходными тегами цвета — дальше edit.py render сведёт в SDR как обычный клип с айфона
        enc = ["-c:v", "libx265", "-crf", "14", "-preset", "medium", "-tag:v", "hvc1", "-x265-params", "log-level=error",
               "-color_primaries", s.get("color_primaries", "bt2020"), "-color_trc", s["color_transfer"],
               "-colorspace", s.get("color_space", "bt2020nc")]
    else:
        enc = ["-c:v", "libx264", "-crf", "14", "-preset", "medium", "-color_primaries", "bt709", "-color_trc", "bt709",
               "-colorspace", "bt709"]
    subprocess.run(["ffmpeg", "-v", "error", "-y", "-i", src, "-filter_complex", fc, "-map", "[v]", "-map", "0:a?",
                    *enc, "-c:a", "copy", "-movflags", "+faststart", out], check=True)
    print(out, f"— {len(regs)} пятн{'о' if len(regs) == 1 else 'а'}{', HDR сохранён' if hdr else ''}")


if __name__ == "__main__":
    if len(sys.argv) != 5 or sys.argv[1] not in ("check", "render"):
        sys.exit(__doc__)
    {"check": check, "render": render}[sys.argv[1]](*sys.argv[2:])
