#!/usr/bin/env python3
"""Сборка вертикальных роликов: расшифровка → нарезка по словам → громкость → субтитры → вшивание.

    edit.py transcribe <video|audio> <out.json> [local|openai]  расшифровка с таймингами слов (по умолчанию локально, mlx-whisper)
    edit.py words <words.json> <from> <to>            слова с таймингами в диапазоне секунд
    edit.py sheet <video> <out.jpg> [every_sec]       раскадровка — посмотреть глазами
    edit.py render <cuts.json> <out.mp4>              нарезка + приведение громкости к -14 LUFS
    edit.py mapwords <cuts.json> <out.json>          слова результата из расшифровок исходников в tx/ (без Whisper)
    edit.py captions <words.json> <cuts.json> <out.ass> [style]   субтитры с пословной подсветкой
                                                     стили: a|b|c|d (плашка) и e (капс + рукописный, как у Соболева)
    edit.py burn <video> <captions.ass> <out.mp4>     вшить субтитры
    edit.py frames <out.jpg> <cols> <file:sec> ...    кадры в нужные секунды, подписанные, сеткой — стыки, реквизит
    edit.py onsets <file> <from> <to> [dB]            отрезки речи (silencedetect) — точные начала фраз
    edit.py envelope <file> <from> <to> [ms]          огибающая громкости — ритм фразы, где кончается слово
    edit.py denoise <video> <out> [atten_dB]         ИИ-шумодав (DeepFilterNet) — копия с чистым звуком
    edit.py facetrack <file> <from> <to> [step]      точки лица для zoom.track (macOS Vision), JSON

cuts.json:
    {
      "src": "~/Downloads/video.MOV",              // общий исходник (опц., если у кусков свои)
      "size": [1080, 1920],                        // кадр результата (по умолчанию так)
      "fit": "crop",                               // как вписывать чужой формат: crop | pad
      "segments": [
        [13.00, 14.15, 1.10, "У меня раньше"],    // start, end, speed, note — из общего src
        {"src": "~/clips/IMG_6266.MOV", "start": 5, "end": 9, "speed": 1.0,
         "note": "клип со своим исходником", "fit": "pad"},
        {"start": 63.4, "end": 64.9, "zoom": {"scale": 1.6, "cx": 0.45, "cy": 0.55},
         "note": "укрупнение: окно в 1/1.6 кадра вокруг точки (cx, cy) — доли повёрнутого кадра, 0.5 = центр;
                  scale_x/scale_y — по осям отдельно: 2.0/1.0 из кадра 2.4:1 вырежет 1.2:1 (с fit pad — кино крупнее)"},
        {"src": "~/clips/IMG_6266.MOV", "start": 33.7, "end": 38.2,
         "audio": {"src": "~/clips/meme.mp4", "start": 0.26, "end": 4.72},
         "note": "видео своё, звук — из мема (липсинк); end у audio опц., короче куска — добьётся тишиной"},
        {"src": "~/clips/IMG_6266.MOV", "start": 41.2, "end": 42.0, "freeze": true,
         "audio": {"src": "~/sfx/scratch.mp3", "start": 0, "end": 0.8},
         "note": "стоп-кадр: кадр в start держится end-start секунд (speed не участвует); звук — из audio или тишина"},
        {"start": 70.2, "end": 72.0,
         "sfx": [{"src": "sfx/memes/Memes-Comedy/SFX_Golden-Swoosh.mp3", "at": -0.3},
                 {"src": "sfx/memes/Memes-Comedy/SFX_Badum-Tssss.mp3", "at": 1.2, "gain": 0, "start": 0, "end": 1.5}],
         "note": "звуки поверх куска: at — с от начала куска в результате (< 0 — до склейки), громкость к речи + gain (по умолч. −3)"}
      ],
      "bed": {"src": "~/clips/wheels.wav", "start": 0, "gain": -14},   // подложка под весь ролик: звук
                                                   // зацикливается, микшируется под куски (стук колёс, музыка)
      "match_loudness": true,                      // громкость каждого куска подгоняется к общему уровню (опц., вкл.);
                                                   // у куска можно задать "gain": дБ вручную вместо автоподгонки
      "captions": {"max_chars": 28,                // опц.: длина субтитра, принудительные разрывы —
                   "margin_v": 560,                // отступ субтитров от низа (px при ширине 1080; по умолчанию 560)
                   "breaks": [["ставьте"], ["у", "меня"]],    // перед первым словом каждой последовательности,
                   "joins": [["не", "любой", "прям", "любой"]], // а эти последовательности не разрывать никогда,
                   "drop": [[9.4, 10.1]],                     // окна (с), где Whisper выдумал слова на тишине
                   "script": [["мне", "10", "месяцев"]],      // только для стиля e: эти слова — рукописным и строчными,
                                                              // остальные капсом; строка ломается по границе между ними
                   "retime": [[55.1, 56.3, null]],            // слово, начавшееся около 55.1 с результата: новые start/end
                                                              // (null — не менять) — показать подпись позже/дольше, чем звук
                   "speakers": [[0, 4.2, "b"]],               // только для стиля g: окна, где говорит «b» (цвет плашки);
                                                              // иначе берётся "speaker" у куска, по умолчанию «a»
                   "palette": {"a": ["#F06800", "#FFFFFF"], "b": ["#FFFFFF", "#F06800"]}},  // g: [плашка, текст]
      "fix": [[["любой", "ставьте"], ["Любой", "боец", "ставьте"]]]  // в fix слов может стать больше/меньше —
                                                                       // тайминги раскладываются по длине слов
      "merge": [["какую", "нибудь", "какую-нибудь"]],             // склеить два слова в одно (опц.)
      "fix":   [[["у", "этот", "журнал"], ["в", "этот", "журнал"]]] // заменить ослышки (опц.)
    }

HDR-исходники с айфона (HLG/PQ, 10 бит) распознаются сами и приводятся к SDR bt709 —
без этого при перекодировании в H.264 цвета выцветают. Поворот из метаданных ffmpeg
применяет сам: клип, у которого ffprobe показывает 1920×1080, на деле может быть вертикальным.
"""
import json
import os
import re
import shutil
import subprocess
import sys
from pathlib import Path

ENV_FILE = Path(__file__).resolve().parent.parent / ".env"   # OPENAI_API_KEY=… в корне репо (опционально)
LABEL_FONT = "/System/Library/Fonts/Supplemental/Arial.ttf"
FONTS_DIR = Path(__file__).resolve().parent / "fonts"   # шрифты рядом с edit.py — libass берёт их оттуда
LOUDNESS = "I=-14:TP=-1.5:LRA=11"
# "audio_fx" в cuts.json: имя пресета или своя цепочка ffmpeg -af. home — телефон лежит в комнате:
# срез гула, шумодав, выравнивание тихих и громких голосов (мама далеко, ребёнок кричит в микрофон)
AUDIO_FX = {
    "home": "highpass=f=80,afftdn=nf=-42:tn=1,speechnorm=e=6:r=0.00008:l=1,alimiter=limit=0.89",
    "voice": "highpass=f=80,speechnorm=e=6:r=0.00008:l=1,alimiter=limit=0.89",   # после denoise
    "home-soft": "highpass=f=80,afftdn=nf=-42:tn=1,acompressor=threshold=-30dB:ratio=3:attack=10:release=250:makeup=4,alimiter=limit=0.89",
}


def run(args, **kw):
    return subprocess.run(args, check=True, **kw)


def openai_key():
    key = os.environ.get("OPENAI_API_KEY")
    if not key and ENV_FILE.exists():
        for line in ENV_FILE.read_text().splitlines():
            if line.startswith("OPENAI_API_KEY="):
                key = line.split("=", 1)[1].strip().strip("\"'")
    if not key:
        sys.exit(f"OPENAI_API_KEY не задан и не найден в {ENV_FILE}")
    return key


def probe(path):
    out = run(["ffprobe", "-v", "error", "-select_streams", "v:0",
               "-show_entries", "stream=width,height:format=duration", "-of", "json", path],
              capture_output=True, text=True).stdout
    data = json.loads(out)
    stream = data["streams"][0]
    return int(stream["width"]), int(stream["height"]), float(data["format"]["duration"])


def duration_of(path):
    """Длительность файла — в отличие от probe() работает и на звуковых файлах без видеодорожки."""
    out = run(["ffprobe", "-v", "error", "-show_entries", "format=duration", "-of", "json", path],
              capture_output=True, text=True).stdout
    return float(json.loads(out)["format"]["duration"])


def load_cuts(path):
    data = json.load(open(path))
    if "src" in data:
        data["src"] = os.path.expanduser(data["src"])
    data.setdefault("size", [1080, 1920])
    data.setdefault("fit", "crop")
    return data


def segment_fields(seg, cuts):
    """Кусок — список [start, end, speed, note] из общего src или объект со своим src и fit."""
    if isinstance(seg, dict):
        src = os.path.expanduser(seg["src"]) if seg.get("src") else cuts["src"]
        return seg["start"], seg["end"], seg.get("speed", 1.0), src, seg.get("fit") or cuts["fit"]
    start, end, speed, *_ = seg
    return start, end, speed, cuts["src"], cuts["fit"]


def is_hdr(path):
    # csv-вывод ffprobe 7.x заканчивается запятой («arib-std-b67,») — из-за неё HDR раньше не распознавался
    transfer = run(["ffprobe", "-v", "error", "-select_streams", "v:0", "-show_entries",
                    "stream=color_transfer", "-of", "default=nw=1:nk=1", path],
                   capture_output=True, text=True).stdout.strip().strip(",")
    return transfer in ("arib-std-b67", "smpte2084")


# ---------------------------------------------------------------- transcribe

def transcribe(src, out_json, mode="local"):
    """mode="local" (по умолчанию) — mlx-whisper на маке, бесплатно, тот же формат JSON (text/segments/words);
    mode="openai" — прежний путь через API (стоит денег)."""
    if mode == "local":
        return transcribe_local(src, out_json)
    tmp = Path(out_json).with_suffix(".mp3")
    run(["ffmpeg", "-v", "error", "-y", "-i", src, "-vn", "-ac", "1", "-ar", "16000", "-b:a", "48k", str(tmp)])
    run(["curl", "-sS", "https://api.openai.com/v1/audio/transcriptions",
         "-H", f"Authorization: Bearer {openai_key()}",
         "-F", f"file=@{tmp}", "-F", "model=whisper-1", "-F", "response_format=verbose_json",
         "-F", "timestamp_granularities[]=word", "-F", "timestamp_granularities[]=segment",
         "-o", out_json])
    tmp.unlink()
    data = json.load(open(out_json))
    if "error" in data:
        sys.exit(data["error"])
    for seg in data.get("segments", []):
        print(f"{seg['start']:7.2f} - {seg['end']:7.2f}  {seg['text'].strip()}")
    print(f"\n{len(data.get('words', []))} слов, {data.get('duration', 0):.1f} с", file=sys.stderr)


def transcribe_local(src, out_json):
    """Локальный Whisper (mlx-whisper, модель large-v3-turbo, русский принудительно). Пишет JSON в формате
    verbose_json: text, segments[start,end,text], words[word,start,end]. Первый запуск качает модель (~1.6 ГБ)."""
    import warnings
    warnings.filterwarnings("ignore")
    import mlx_whisper
    tmp = Path(out_json).with_suffix(".16k.wav")   # не .wav: иначе затрёт сам себе вход, если на входе wav

    run(["ffmpeg", "-v", "error", "-y", "-i", src, "-vn", "-ac", "1", "-ar", "16000", str(tmp)])
    r = mlx_whisper.transcribe(str(tmp), path_or_hf_repo="mlx-community/whisper-large-v3-turbo",
                               language="ru", word_timestamps=True)
    tmp.unlink()
    segs = r.get("segments", [])
    data = {"task": "transcribe", "language": "ru", "text": r.get("text", "").strip(),
            "duration": duration_of(src),
            "segments": [{"id": i, "start": s["start"], "end": s["end"], "text": s["text"]} for i, s in enumerate(segs)],
            "words": [{"word": w["word"].strip(), "start": w["start"], "end": w["end"]}
                      for s in segs for w in s.get("words", [])]}
    json.dump(data, open(out_json, "w"), ensure_ascii=False, indent=1)
    for seg in data["segments"]:
        print(f"{seg['start']:7.2f} - {seg['end']:7.2f}  {seg['text'].strip()}")
    print(f"\n{len(data['words'])} слов, {data['duration']:.1f} с (локально)", file=sys.stderr)


def words(words_json, start, end):
    items = json.load(open(words_json))["words"]
    print(" ".join(f"{w['word']}[{w['start']:.2f}-{w['end']:.2f}]" for w in items if start <= w["start"] <= end))


# ---------------------------------------------------------------- sheet

def sheet(src, out_jpg, every=5, cols=5):
    _, _, duration = probe(src)
    rows = max(1, -(-int(duration // every + 1) // cols))
    label = f"drawtext=fontfile={LABEL_FONT}:text='%{{eif\\:n*{every}\\:d}}s':x=4:y=4:fontsize=22:fontcolor=yellow:box=1:boxcolor=black@0.7"
    run(["ffmpeg", "-v", "error", "-y", "-i", src,
         "-vf", f"fps=1/{every},scale=200:-1,{label},tile={cols}x{rows}",
         "-frames:v", "1", out_jpg])
    print(out_jpg)


# ---------------------------------------------------------------- render

# HDR (HLG/PQ) → SDR bt709. Линейный свет, тон-кривая Хейбла, обратно в bt709.
# После тон-маппинга картинка чуть площе, чем HDR на экране айфона, — лёгкая насыщенность возвращает сочность.
SDR_SATURATION = 1.15
TONEMAP = ("zscale=t=linear:npl=100,format=gbrpf32le,zscale=p=bt709,"
           f"tonemap=hable:desat=0,zscale=t=bt709:m=bt709:r=tv,eq=saturation={SDR_SATURATION}")


SEGMENT_LEVEL = -18.0   # LUFS, к которому подгоняется каждый кусок до общего прохода к -14


def segment_loudness(src, start, end):
    """Интегральная громкость отрывка (LUFS) или None, если тишина."""
    r = subprocess.run(["ffmpeg", "-v", "info", "-ss", f"{start:.3f}", "-t", f"{end - start:.3f}", "-i", src,
                        "-vn", "-af", f"loudnorm={LOUDNESS}:print_format=json", "-f", "null", "-"],
                       capture_output=True, text=True)
    m = re.search(r'"input_i"\s*:\s*"(-?[\d.]+|-inf)"', r.stderr)
    if not m or m.group(1) == "-inf":
        return None
    return float(m.group(1))


def segment_gain(src, start, end):
    lufs = segment_loudness(src, start, end)
    return 0.0 if lufs is None else max(-20.0, min(25.0, SEGMENT_LEVEL - lufs))


def track_expr(track, start, speed):
    """Выражения ffmpeg для cx(t), cy(t) по ключевым точкам [секунда_исходника, cx, cy]: кусочно-линейно,
    t — время внутри куска (после trim/setpts), до первой точки и после последней — крайние значения."""
    pts = sorted((round((t - start) / speed, 3), cx, cy) for t, cx, cy in track)

    def build(idx):
        expr = f"{pts[-1][idx]}"
        for (t0, *a), (t1, *b) in reversed(list(zip(pts, pts[1:]))):
            v0, v1 = a[idx - 1], b[idx - 1]
            seg = f"{v0}+({v1}-{v0})*(t-{t0})/{t1 - t0}" if t1 > t0 else f"{v1}"
            expr = f"if(lt(t,{t1}),{seg},{expr})"
        return f"if(lt(t,{pts[0][0]}),{pts[0][idx]},{expr})"

    return build(1), build(2)


def render(cuts_path, out):
    cuts = load_cuts(cuts_path)
    width, height = cuts["size"]
    match = cuts.get("match_loudness", True)
    sources, hdr, fc, total, notes, sfx_hits = [], {}, [], 0.0, [], []

    def index(src):
        if src not in sources:
            sources.append(src)
            hdr[src] = is_hdr(src)
        return sources.index(src)

    def audio_span(seg):
        """(src, start, end) чужого звука у куска — чтобы понять, продолжается ли звук в соседнем куске."""
        audio = seg.get("audio") if isinstance(seg, dict) else None
        if not audio:
            return None
        start, end, speed, *_ = segment_fields(seg, cuts)
        dur = (end - start) / speed
        a_start = audio["start"]
        return os.path.expanduser(audio["src"]), a_start, min(audio.get("end", a_start + dur), a_start + dur)

    def contiguous(a, b):
        """Звук куска b продолжает звук куска a без разрыва — фейды на стыке не нужны, иначе провал в речи."""
        return a and b and a[0] == b[0] and abs(a[2] - b[1]) < 0.005

    segs = cuts["segments"]
    for i, seg in enumerate(segs):
        start, end, speed, src, fit = segment_fields(seg, cuts)
        n = index(src)
        dur = (end - start) / speed
        span = audio_span(seg)
        fade_in = "" if i > 0 and contiguous(audio_span(segs[i - 1]), span) else "afade=t=in:st=0:d=0.04,"
        fade_out = ("" if i + 1 < len(segs) and contiguous(span, audio_span(segs[i + 1]))
                    else f"afade=t=out:st={dur - 0.06:.3f}:d=0.06,")
        if fit == "pad":
            geo = (f"scale={width}:{height}:force_original_aspect_ratio=decrease,"
                   f"pad={width}:{height}:(ow-iw)/2:(oh-ih)/2")
        else:
            geo = f"scale={width}:{height}:force_original_aspect_ratio=increase,crop={width}:{height}"
        tone = TONEMAP + "," if hdr[src] else ""
        zoom = seg.get("zoom") if isinstance(seg, dict) else None
        if zoom:
            # укрупнение: окно в 1/scale кадра вокруг точки (cx, cy) в долях уже повёрнутого кадра;
            # "track": [[секунда_исходника, cx, cy], …] — окно едет за лицом, между точками линейно
            z = zoom.get("scale", 1.0)
            zx, zy = zoom.get("scale_x", z), zoom.get("scale_y", z)   # по осям отдельно — сменить пропорции кадра
            if zoom.get("track"):
                cx, cy = track_expr(zoom["track"], start, speed)
            else:
                cx, cy = zoom.get("cx", 0.5), zoom.get("cy", 0.5)
            if zoom.get("dy"):   # окно ниже точки на dy долей кадра — лицо уходит в верхнюю часть, над субтитром
                cy = f"({cy})+{zoom['dy']}"
            zf = (f"crop=w=iw/{zx}:h=ih/{zy}:x='min(max(iw*({cx})-ow/2,0),iw-ow)':y='min(max(ih*({cy})-oh/2,0),ih-oh)',")
        else:
            zf = ""
        freeze = isinstance(seg, dict) and seg.get("freeze")
        if freeze:
            # стоп-кадр: один кадр в start, размноженный на dur секунд (tpad клонирует последний кадр)
            dur = end - start
            vsrc = (f"[{n}:v]trim=start={start}:end={start + 0.04},setpts=PTS-STARTPTS,"
                    f"tpad=stop_mode=clone:stop_duration={dur:.3f},trim=duration={dur:.3f},setpts=PTS-STARTPTS,")
        else:
            vsrc = f"[{n}:v]trim=start={start}:end={end},setpts=(PTS-STARTPTS)/{speed},"
        # поворот из displaymatrix ffmpeg уже применил к кадрам; если кусок начинается с нулевой
        # секунды, эта метка едет дальше как side data кадра и попадает в готовый файл — плеер
        # разворачивает вертикальный ролик набок. Снимаем метку, геометрию это не трогает.
        fc.append(vsrc + f"sidedata=mode=delete:type=DISPLAYMATRIX,{zf}{tone}{geo},"
                         f"fps=30,setsar=1,format=yuv420p[v{i}]")
        tail = (f"aresample=44100,aformat=channel_layouts=stereo,"
                f"{fade_in}{fade_out}aformat=channel_layouts=stereo[a{i}]")
        audio = seg.get("audio") if isinstance(seg, dict) else None
        if audio:
            # звук из другого файла (например, мем поверх своего липсинка), без изменения темпа
            a_src = os.path.expanduser(audio["src"])
            a_start = audio["start"]
            a_end = min(audio.get("end", a_start + dur), a_start + dur)
            m = index(a_src)
            gain = seg["gain"] if "gain" in seg else (segment_gain(a_src, a_start, a_end) if match else 0.0)
            fc.append(f"[{m}:a]atrim=start={a_start}:end={a_end},asetpts=PTS-STARTPTS,volume={gain:.1f}dB,"
                      f"apad=whole_dur={dur:.3f},atrim=end={dur:.3f}," + tail)
            notes.append(f"{i}: звук {Path(a_src).name} {a_start}-{a_end:.2f}, {gain:+.1f} дБ")
        elif freeze:
            # стоп-кадр без своего звука — тишина
            fc.append(f"[{n}:a]atrim=start={start}:end={start + 0.02},asetpts=PTS-STARTPTS,volume=-90dB,"
                      f"apad=whole_dur={dur:.3f},atrim=end={dur:.3f}," + tail)
            notes.append(f"{i}: стоп-кадр, тишина")
        else:
            gain = (seg["gain"] if isinstance(seg, dict) and "gain" in seg
                    else segment_gain(src, start, end) if match else 0.0)
            fc.append(f"[{n}:a]atrim=start={start}:end={end},asetpts=PTS-STARTPTS,atempo={speed},"
                      f"volume={gain:.1f}dB," + tail)
            notes.append(f"{i}: {gain:+.1f} дБ")
        # звуки поверх куска (вжух на зуме, «ба-дум-тсс» на панче): at — секунды от начала куска
        # в результате, может быть < 0 (вжух начинается до склейки); громкость — к уровню речи + gain
        for fx in (seg.get("sfx", []) if isinstance(seg, dict) else []):
            f_src = os.path.expanduser(fx["src"])
            f_start = fx.get("start", 0.0)
            f_end = fx.get("end") or f_start + duration_of(f_src)
            f_gain = segment_gain(f_src, f_start, f_end) + fx.get("gain", -3.0)
            sfx_hits.append((index(f_src), f_start, f_end, f_gain, max(total + fx.get("at", 0.0), 0.0)))
            notes.append(f"{i}: sfx {Path(f_src).name} @{total + fx.get('at', 0.0):.2f} с, {f_gain:+.1f} дБ")
        total += dur
    count = len(cuts["segments"])
    fc.append("".join(f"[v{i}][a{i}]" for i in range(count)) + f"concat=n={count}:v=1:a=1[vc][a]")
    # после concat кодек берёт цветовые теги из кадров, а не из опций -color_*; закрепляем SDR явно
    fc.append("[vc]setparams=color_primaries=bt709:color_trc=bt709:colorspace=bt709[v]")
    hdr_note = ", HDR → SDR: " + ", ".join(Path(s).name for s in sources if hdr[s]) if any(hdr.values()) else ""
    print(f"{count} кусков из {len(sources)} исходников → {total:.1f} с{hdr_note}", file=sys.stderr)
    if match:
        print("громкость кусков: " + "; ".join(notes), file=sys.stderr)

    # чистка звука всего ролика после склейки (шумодав, компрессия тихой домашней записи) — до подложки
    amap = "[a]"
    if cuts.get("audio_fx"):
        fx = AUDIO_FX.get(cuts["audio_fx"], cuts["audio_fx"])
        fc.append(f"[a]{fx},aresample=44100,aformat=channel_layouts=stereo[afx]")
        amap = "[afx]"
        print(f"звук: {fx}", file=sys.stderr)

    if sfx_hits:
        for k, (m, s, e, g, at) in enumerate(sfx_hits):
            fc.append(f"[{m}:a]atrim=start={s}:end={e},asetpts=PTS-STARTPTS,aresample=44100,"
                      f"aformat=channel_layouts=stereo,volume={g:.1f}dB,afade=t=out:st={max(e - s - 0.03, 0):.3f}:d=0.03,"
                      f"adelay={int(at * 1000)}:all=1[sfx{k}]")
        fc.append(amap + "".join(f"[sfx{k}]" for k in range(len(sfx_hits)))
                  + f"amix=inputs={len(sfx_hits) + 1}:duration=first:dropout_transition=0:normalize=0[asfx]")
        amap = "[asfx]"

    # подложка: непрерывный звук под всем роликом (стук колёс, шум зала, музыка) — зацикливается
    bed = cuts.get("bed")
    inputs = [arg for src in sources for arg in ("-i", src)]
    if bed:
        b_src = os.path.expanduser(bed["src"])
        b_start, b_gain = bed.get("start", 0.0), bed.get("gain", -12.0)
        fc.append(f"[{len(sources)}:a]atrim=start={b_start},asetpts=PTS-STARTPTS,aresample=44100,"
                  f"aformat=channel_layouts=stereo,volume={b_gain:.1f}dB,atrim=end={total:.3f},"
                  f"afade=t=in:st=0:d=0.4,afade=t=out:st={max(total - 0.8, 0):.3f}:d=0.8[bed]")
        fc.append(f"{amap}[bed]amix=inputs=2:duration=first:dropout_transition=0:normalize=0[am]")
        inputs += ["-stream_loop", "-1", "-i", b_src]
        amap = "[am]"
        print(f"подложка: {Path(b_src).name} {b_gain:+.1f} дБ", file=sys.stderr)

    raw = Path(out).with_suffix(".raw.mkv")
    run(["ffmpeg", "-v", "error", "-y", *inputs, "-filter_complex", ";".join(fc),
         "-map", "[v]", "-map", amap, "-c:v", "libx264", "-preset", "medium", "-crf", os.environ.get("EDIT_CRF", "19"),
         "-pix_fmt", "yuv420p", "-color_primaries", "bt709", "-color_trc", "bt709", "-colorspace", "bt709",
         "-r", "30", "-c:a", "pcm_s16le", str(raw)])
    normalize(str(raw), out)
    raw.unlink()


def normalize(src, out):
    """Два прохода EBU R128 к -14 LUFS — уровень, к которому Instagram и YouTube приводят звук сами."""
    measure = subprocess.run(["ffmpeg", "-v", "info", "-i", src, "-af",
                              f"loudnorm={LOUDNESS}:print_format=json", "-f", "null", "-"],
                             capture_output=True, text=True)
    m = json.loads(re.search(r"\{[^{]*input_i.*?\}", measure.stderr, re.S).group(0))
    print(f"громкость {m['input_i']} LUFS → -14", file=sys.stderr)
    run(["ffmpeg", "-v", "error", "-y", "-i", src, "-af",
         f"loudnorm={LOUDNESS}:measured_I={m['input_i']}:measured_TP={m['input_tp']}"
         f":measured_LRA={m['input_lra']}:measured_thresh={m['input_thresh']}"
         f":offset={m['target_offset']}:linear=true,aresample=44100",
         "-c:v", "copy", "-c:a", "aac", "-b:a", "160k", "-movflags", "+faststart", out])


# ---------------------------------------------------------------- captions

ASS_HEADER = """[Script Info]
ScriptType: v4.00+
PlayResX: {w}
PlayResY: {h}
WrapStyle: 0
ScaledBorderAndShadow: yes

[V4+ Styles]
Format: Name, Fontname, Fontsize, PrimaryColour, SecondaryColour, OutlineColour, BackColour, Bold, Italic, Underline, StrikeOut, ScaleX, ScaleY, Spacing, Angle, BorderStyle, Outline, Shadow, Alignment, MarginL, MarginR, MarginV, Encoding
Style: Cap,{font},{size},&H00FFFFFF,&H000000FF,{outline_c},&H90000000,{bold},0,0,0,100,100,{spacing},0,1,{outline},{shadow},2,{margin_lr},{margin_lr},{margin_v},204

[Events]
Format: Layer, Start, End, Style, Name, MarginL, MarginR, Effect, Text
"""

# Цвета в ASS — &HBBGGRR. Терракота #b9603a → &H003A60B9, светлая #e08a5a → &H005A8AE0.
# Размеры заданы для ширины 1080 и масштабируются под реальную.
STYLES = {
    "a": dict(font="Arial Black", size=74, bold=0, spacing=0, hi="&H005A8AE0", marker=None, max_chars=20),
    "b": dict(font="Futura", size=86, bold=1, spacing=1, hi="&H005A8AE0", marker=None, max_chars=24),
    "c": dict(font="Arial Black", size=74, bold=0, spacing=0, hi="&H00FFFFFF", marker="&H003A60B9", max_chars=20),
    "d": dict(font="Futura", size=86, bold=1, spacing=1, hi="&H00FFFFFF", marker="&H003A60B9", max_chars=26),
    # «e» — как у Соболева: ключевые слова капсом, вводные (список "script" в cuts.json) — рукописным
    # строчными и помельче, произносимое слово жёлтым, плашки нет, субтитр по центру кадра, а не внизу
    "e": dict(font="Alumni Black", size=120, bold=0, spacing=0, hi="&H002AD2F5", marker=None, max_chars=22,
              upper=True, script_font="Marck Script", script_size=0.72, outline=6, shadow=4,
              margin_v=740, margin_lr=70),
    # «f» — кинетический, как у Соболева: строки появляются по одной сверху вниз, каждая со своим
    # размером, сдвигом по горизонтали и въездом слева; жёлтый — постоянный признак строки-панча
    "f": dict(font="Alumni Black", size=142, bold=0, spacing=0, hi="&H002AD2F5", marker=None, max_chars=30,
              upper=True, script_font="Marck Script", script_size=0.78, accent_size=1.34,
              outline=5, shadow=3, margin_v=740, margin_lr=40, kinetic=True,
              top=880, line_chars=15, offsets=[-0.05, 0.07, -0.06, 0.04], rise=200),
    # «h» — Соболев, второй заход (разбор покадрово 25.09): обводки нет, только мягкая тень; строки стоят
    # плотно, рукописная — того же роста, что капс; анимируется одно жёлтое слово-панч: влетает из-за левого
    # края по буквам (правые впереди, левые догоняют), тормозит; остальное появляется без анимации
    "h": dict(font="Oswald Bold", size=109, bold=0, spacing=0, hi="#F6E409", marker=None, max_chars=34,
              upper=True, script_font="Bad Script", script_size=1.42, outline=0, shadow=0, margin_v=740,
              margin_lr=40, kinetic2=True, top=840, line_chars=14, offsets=[-0.08, 0.07, -0.05, 0.05],
              accent_width=0.62, accent_min=1.3, accent_max=3.0, fly=0.48, stagger=0.012,
              shadow_blur=7, shadow_alpha="60", shadow_off=(3, 5)),
    # «g» — как у Джимми Карра (его рилсы с crowdwork): кусок фразы в 1–3 слова капсом на скруглённой плашке,
    # появляется целиком, без подсветки слов; цвет плашки — кто говорит (у Карра оранжевая, у зрителя белая
    # с оранжевым текстом). Говорящий — "speaker" у куска или окна "speakers" в captions
    "g": dict(font="Arial Black", size=74, bold=0, spacing=0, hi=None, marker=None, max_chars=18, max_dur=1.4,
              upper=True, outline=3, shadow=2, pill_h=97, pill_pad=34, pill_r=0.3,
              palette={"a": ["#F06800", "#FFFFFF"], "b": ["#FFFFFF", "#F06800"], "c": ["#FFD21F", "#1A1A1A"]}),
}
CAPTION_MARGIN_V = 560   # px от низа при ширине 1080: выше подписи и кнопок Reels (360 оказалось низко)
CAPTION_TAIL = 0.35   # сколько субтитр висит после конца последнего слова (Whisper обрезает концы слов рано)
IDLE = "&H00FFFFFF"
OUTLINE_C = "&H00101010"
DEFAULT_MERGE = [["какую", "нибудь", "какую-нибудь"], ["gpt", "шку", "GPT-шку"]]


def clean_words(items, merge, fix):
    merge_map = {(a.lower(), b.lower()): c for a, b, c in merge}
    out = []
    for w in items:
        # тире расшифровка ставит как отдельное «слово» (диалог в одном клипе) — в субтитрах оно мусор
        w = {"word": w["word"].strip(" ,.!?;:«»—-\"'"), "start": w["start"], "end": w["end"]}
        if not w["word"]:
            continue
        if out and (out[-1]["word"].lower(), w["word"].lower()) in merge_map:
            out[-1]["word"] = merge_map[(out[-1]["word"].lower(), w["word"].lower())]
            out[-1]["end"] = w["end"]
            continue
        out.append(w)
    for src, dst in fix:
        src = [s.lower() for s in src]
        i = 0
        while i <= len(out) - len(src):
            if [x["word"].lower() for x in out[i:i + len(src)]] != src:
                i += 1
                continue
            if len(dst) == len(src):
                for j, word in enumerate(dst):
                    out[i + j]["word"] = word
            else:
                # число слов изменилось (Whisper проглотил слово) — раскладываем общий отрезок по длине слов
                t0, t1 = out[i]["start"], out[i + len(src) - 1]["end"]
                total = sum(len(w) for w in dst) or 1
                items, t = [], t0
                for word in dst:
                    t_end = t + (t1 - t0) * len(word) / total
                    items.append({"word": word, "start": t, "end": t_end})
                    t = t_end
                out[i:i + len(src)] = items
            i += len(dst)
    return out


def cut_points(cuts):
    """Моменты склейки монтажа — субтитр не должен через них перешагивать."""
    points, t = [], 0.0
    for seg in cuts["segments"]:
        start, end, speed, *_ = segment_fields(seg, cuts)
        t += (end - start) / speed
        points.append(round(t, 3))   # без округления 17.1 < 17.100000000001 — и слово на стыке уходит в отдельный субтитр
    return points


def find_seq(items, seq):
    seq = [x.lower() for x in seq]
    return [i for i in range(len(items) - len(seq) + 1)
            if [x["word"].lower() for x in items[i:i + len(seq)]] == seq]


def group(items, max_chars, cuts_at, max_gap=0.45, max_dur=2.2, breaks=(), joins=()):
    """breaks — списки слов: перед первым словом каждой такой последовательности начинается новый субтитр.
    joins — последовательности, внутри которых разрыва не будет никогда (Whisper промахнулся таймингом у склейки)."""
    forced = {i for seq in breaks for i in find_seq(items, seq)}
    glued = {i + j for seq in joins for i in find_seq(items, seq) for j in range(1, len(seq))}
    groups, cur = [], []
    for wi, w in enumerate(items):
        if cur and wi in glued:
            cur.append(w)
            continue
        # слово не может перешагнуть склейку: предыдущее началось до неё, это — на ней или после
        # (по началу слов: конец слова Whisper часто растягивает за склейку)
        crosses = cur and any(cur[-1]["start"] < c <= w["start"] + 0.15 for c in cuts_at)
        if cur and (crosses or wi in forced
                    or sum(len(x["word"]) + 1 for x in cur) + len(w["word"]) > max_chars
                    or w["start"] - cur[-1]["end"] > max_gap
                    or w["end"] - cur[0]["start"] > max_dur):
            groups.append(cur)
            cur = []
        cur.append(w)
    if cur:
        groups.append(cur)
    # строка не должна заканчиваться висящим предлогом. Куда его девать — решает пауза:
    # в «…приходим домой | я беру ключи» слово «я» ближе к «беру», и уезжает вперёд,
    # а в «короче я на ПП | Но это не мой выбор» после «ПП» пауза — и оно остаётся на месте
    # (по одной длине слова «ПП» утаскивало за собой и «на», и «я»)
    glued_ids = {id(items[i]) for i in glued}
    for i in range(len(groups) - 1):
        while len(groups[i]) > 1 and len(groups[i][-1]["word"]) <= 2:
            w = groups[i][-1]
            if id(w) in glued_ids:   # «joins» держит и здесь: в монотонной начитке пауз нет совсем
                break
            after = groups[i + 1][0]["start"] - w["end"]
            before = w["start"] - groups[i][-2]["end"]
            if after - before > 0.15:   # запас: у «пойти в | барбершоп» обе паузы нулевые, решает только явная
                break
            groups[i + 1].insert(0, groups[i].pop())
    return groups


def script_break(script):
    """Рукописная часть и капс — всегда разными строками; None — обычное деление по длине."""
    if not any(script) or all(script):
        return None
    edges = [i for i in range(1, len(script)) if script[i] != script[i - 1]]
    return edges[0] if len(edges) == 1 else None


def static_events(prepared, st, k):
    """Субтитры стилей a–e: весь текст стоит на месте, по словам бежит подсветка."""
    outline = st.get("outline", 5)
    events = []
    for g, script, _, tail in prepared:
        # в стиле «e» капс и рукописный различаются регистром: ключевые слова КАПСОМ, вводные — строчными
        text = [(w["word"].lower() if script[j] else w["word"].upper()) if st.get("upper") else w["word"]
                for j, w in enumerate(g)]
        if not st.get("upper"):
            text[0] = text[0][0].upper() + text[0][1:]
        brk = script_break(script) or split_point([len(t) for t in text])
        for wi, w in enumerate(g):
            start = g[0]["start"] if wi == 0 else w["start"]
            end = g[wi + 1]["start"] if wi + 1 < len(g) else tail
            if end <= start:
                continue
            parts = []
            for j, t in enumerate(text):
                colour = st["hi"] if j == wi else IDLE
                pop = "\\fscx106\\fscy106" if j == wi else "\\fscx100\\fscy100"
                mark = ""
                if st["marker"]:
                    mark = (f"\\bord{round(16 * k)}\\3c{st['marker']}" if j == wi
                            else f"\\bord{round(5 * k)}\\3c{OUTLINE_C}")
                face = ""
                if script[j]:
                    face = (f"\\fn{st['script_font']}\\fs{round(st['size'] * st['script_size'] * k)}"
                            f"\\bord{round(outline * 0.7 * k)}")
                elif st.get("script_font"):
                    face = f"\\fn{st['font']}\\fs{round(st['size'] * k)}\\bord{round(outline * k)}"
                parts.append(f"{{\\c{colour}{pop}{mark}{face}}}{t}")
            line = parts[0]
            for j in range(1, len(parts)):
                line += ("\\N" if j == brk else " ") + parts[j]
            fade = "{\\fad(70,0)}" if wi == 0 else ""
            events.append(f"Dialogue: 0,{ass_time(start)},{ass_time(end)},Cap,,0,0,,{fade}{line}")
    return events


def make_lines(g, script, line_chars):
    """Слова субтитра → строки: граница между рукописным и капсом рвёт строку всегда,
    длинный кусок делится пополам. У Соболева строка — это одно-два слова."""
    runs, cur = [], []
    for j, w in enumerate(g):
        if cur and script[j] != script[cur[0]]:
            runs.append(cur)
            cur = []
        cur.append(j)
    if cur:
        runs.append(cur)
    lines = []
    for run in runs:
        while run:
            short_pair = len(run) == 2 and min(len(g[j]["word"]) for j in run) <= 2
            if (sum(len(g[j]["word"]) + 1 for j in run) - 1 <= line_chars
                    or len(run) == 1 or short_pair):
                lines.append(run)
                break
            at = split_point([len(g[j]["word"]) for j in run], min_total=line_chars) or 1
            lines.append(run[:at])
            run = run[at:]
    return lines


def kinetic_events(groups, st, width, k):
    """Субтитры стиля «f»: строка появляется целиком со своим размером, сдвигом и въездом слева,
    и остаётся до конца субтитра. Блок растёт сверху вниз — как в референсе."""
    offsets, events, n = st["offsets"], [], 0
    for g, script, accent, tail in groups:
        lines = make_lines(g, script, st["line_chars"])
        y = st["top"] * k
        for li, idx in enumerate(lines):
            is_script = script[idx[0]]
            hot = any(accent[j] for j in idx)
            size = round(st["size"] * k * (st["script_size"] if is_script
                                           else st["accent_size"] if hot else 1.0))
            text = " ".join(g[j]["word"].lower() if is_script else g[j]["word"].upper() for j in idx)
            x = round(width / 2 + offsets[n % len(offsets)] * width)
            n += 1
            rise = st["rise"]
            tags = (f"\\an8\\fn{st['script_font'] if is_script else st['font']}\\fs{size}"
                    f"\\c{st['hi'] if hot else IDLE}\\bord{round(st['outline'] * k)}"
                    f"\\move({x - round(0.07 * width)},{round(y)},{x},{round(y)},0,{rise})"
                    f"\\fad(90,0)\\fscx118\\t(0,{rise},\\fscx100)")
            events.append((g[idx[0]]["start"],
                           "Dialogue: 0,{t0},{t1},Cap,,0,0,," + "{" + tags + "}" + text, tail))
            y += size * 1.06
    return [e[1].replace("{t0}", ass_time(e[0])).replace("{t1}", ass_time(e[2])) for e in events]


def ass_colour(hex_rgb):
    h = hex_rgb.lstrip("#")
    return f"&H00{h[4:6]}{h[2:4]}{h[0:2]}".upper()


def font_file(family):
    """Файл шрифта по имени семейства — из tools/fonts или системных: нужен, чтобы померить ширину текста."""
    from fontTools.ttLib import TTFont
    dirs = [FONTS_DIR, Path("/System/Library/Fonts/Supplemental"), Path("/System/Library/Fonts"),
            Path.home() / "Library/Fonts", Path("/Library/Fonts")]
    for d in dirs:
        for f in sorted(d.glob("*.[ot]tf")):
            try:
                if TTFont(f, lazy=True)["name"].getDebugName(1) == family:
                    return f
            except Exception:
                continue
    sys.exit(f"шрифт «{family}» не найден — нужен файл, чтобы померить ширину плашки")


def text_width(text, family, size):
    """Ширина строки так, как её нарисует libass: он масштабирует шрифт так, чтобы высота
    ascender+descender (OS/2 win-метрики) равнялась размеру из стиля, а не em."""
    from fontTools.ttLib import TTFont
    font = TTFont(font_file(family))
    upem = font["head"].unitsPerEm
    os2 = font["OS/2"]
    scale = size / (os2.usWinAscent + os2.usWinDescent)
    cmap, hmtx = font.getBestCmap(), font["hmtx"]
    return sum(hmtx[cmap.get(ord(ch), cmap.get(ord("?")))][0] for ch in text) * scale, upem


def pill_path(w, h, r):
    """Скруглённый прямоугольник для \\p1: левый верхний угол в (0, 0), углы — кубическими кривыми."""
    c = r * 0.45   # 1 − 0.55: смещение контрольных точек, чтобы четверть круга была круглой
    return (f"m {r:.0f} 0 l {w - r:.0f} 0 b {w - c:.0f} 0 {w:.0f} {c:.0f} {w:.0f} {r:.0f} "
            f"l {w:.0f} {h - r:.0f} b {w:.0f} {h - c:.0f} {w - c:.0f} {h:.0f} {w - r:.0f} {h:.0f} "
            f"l {r:.0f} {h:.0f} b {c:.0f} {h:.0f} 0 {h - c:.0f} 0 {h - r:.0f} "
            f"l 0 {r:.0f} b 0 {c:.0f} {c:.0f} 0 {r:.0f} 0")


def pill_events(prepared, st, width, height, margin_v, k):
    """Субтитры стиля «g»: плашка-таблетка по ширине текста, текст целиком, цвета — по говорящему."""
    events = []
    size = round(st["size"] * k)
    h, pad = st["pill_h"] * k, st["pill_pad"] * k
    r = h * st["pill_r"]
    bottom = height - margin_v
    for g, _, _, tail, who in prepared:
        text = " ".join(w["word"].upper() for w in g)
        plate, ink = st["palette"].get(who, st["palette"]["a"])
        tw, _ = text_width(text, st["font"], size)
        w = min(tw + 2 * pad, width - 40 * k)
        x0, y0 = (width - w) / 2, bottom - h
        t0, t1 = ass_time(g[0]["start"]), ass_time(tail)
        events.append(f"Dialogue: 0,{t0},{t1},Cap,,0,0,,{{\\an7\\pos({x0:.0f},{y0:.0f})\\bord0\\shad0"
                      f"\\1c{ass_colour(plate)}\\p1}}{pill_path(w, h, r)}")
        events.append(f"Dialogue: 1,{t0},{t1},Cap,,0,0,,{{\\an5\\pos({width / 2:.0f},{y0 + h / 2:.0f})"
                      f"\\1c{ass_colour(ink)}\\3c&H00000000&\\4c&H00000000&"
                      f"\\bord{round(st['outline'] * k)}\\shad{round(st['shadow'] * k)}}}{text}")
    return events


def speaker_of(t, cuts, windows):
    """Кто говорит в момент t результата: окно из captions.speakers, иначе "speaker" куска, иначе "a"."""
    for a, b, who in windows:
        if a <= t < b:
            return who
    pos = 0.0
    for seg in cuts["segments"]:
        start, end, speed, *_ = segment_fields(seg, cuts)
        pos += (end - start) / speed
        if t < pos:
            return seg.get("speaker", "a") if isinstance(seg, dict) else "a"
    return "a"


def font_metrics(family):
    """(ascent, cap_height) в долях размера ASS: libass масштабирует по winAscent+winDescent."""
    from fontTools.ttLib import TTFont
    os2 = TTFont(font_file(family))["OS/2"]
    total = os2.usWinAscent + os2.usWinDescent
    cap = getattr(os2, "sCapHeight", 0) or os2.usWinAscent * 0.7
    xh = getattr(os2, "sxHeight", 0) or cap * 0.6
    return os2.usWinAscent / total, cap / total, xh / total


def fly_in(letters, y, t0, tail, st, width, k, colour, face):
    """Жёлтое слово влетает из-за левого края по буквам: последняя буква стартует первой, каждая следующая
    (справа налево) — на stagger позже, все летят fly секунд с торможением (quadratic ease-out: cubic оседал за 0.2 с, в референсе ~0.4). libass двигает
    \\move только линейно, поэтому траектория — 6 линейных отрезков, у каждого свой Dialogue; границы
    отрезков округлены до сотых, как в ASS, и стыкуются без дыр."""
    events, n, steps = [], len(letters), 6
    ox, oy = (round(v * k) for v in st["shadow_off"])
    for j, (ch, xf, w) in enumerate(letters):
        if not ch.strip():
            continue
        start = t0 + (n - 1 - j) * st["stagger"]
        xs = -w - 10 * k
        ease = lambda u: 1 - (1 - u) ** 2
        cuts_t = [round(start + st["fly"] * i / steps, 2) for i in range(steps + 1)]
        xs_at = [xs + (xf - xs) * ease(i / steps) for i in range(steps + 1)]
        spans = [(cuts_t[i], cuts_t[i + 1], xs_at[i], xs_at[i + 1], 2 if i < 3 else 1 if i < 5 else 0)
                 for i in range(steps)] + [(cuts_t[-1], tail, xf, xf, 0)]
        for a, b, x1, x2, blur in spans:
            if b <= a:
                continue
            mv = f"\\move({x1:.0f},{y:.0f},{x2:.0f},{y:.0f})" if abs(x2 - x1) > 0.5 else f"\\pos({x2:.0f},{y:.0f})"
            mvs = (f"\\move({x1 + ox:.0f},{y + oy:.0f},{x2 + ox:.0f},{y + oy:.0f})" if abs(x2 - x1) > 0.5
                   else f"\\pos({x2 + ox:.0f},{y + oy:.0f})")
            events.append((a, f"Dialogue: 0,{ass_time(a)},{ass_time(b)},Cap,,0,0,,{{\\an7{mvs}{face}\\bord0\\shad0"
                              f"\\1c&H000000&\\1a&H{st['shadow_alpha']}&\\blur{round(st['shadow_blur'] * k)}}}{ch}"))
            events.append((a, f"Dialogue: 1,{ass_time(a)},{ass_time(b)},Cap,,0,0,,{{\\an7{mv}{face}\\bord0\\shad0"
                              f"\\1c{colour}\\blur{blur}}}{ch}"))
    return events


def kinetic2_events(groups, st, width, k):
    """Субтитры стиля «h»: строки субтитра копятся сверху вниз, каждая появляется со своим первым словом
    без анимации; строка из слов "accent" — крупная, жёлтая, по центру и влетает по буквам (fly_in)."""
    asc_c, cap_c, _ = font_metrics(st["font"])
    asc_s, _, xh_s = font_metrics(st["script_font"])
    base = st["size"] * k
    offsets, events, n = st["offsets"], [], 0
    ox, oy = (round(v * k) for v in st["shadow_off"])
    shadow = f"\\bord0\\shad0\\1c&H000000&\\1a&H{st['shadow_alpha']}&\\blur{round(st['shadow_blur'] * k)}"
    for g, script, accent, tail in groups:
        # строки: рукописное, капс и акцент — всегда разными строками; длинный капс делится по line_chars
        runs, cur = [], []
        for j in range(len(g)):
            if cur and (script[j], accent[j]) != (script[cur[0]], accent[cur[0]]):
                runs.append(cur)
                cur = []
            cur.append(j)
        runs.append(cur)
        lines = []
        for run in runs:
            if accent[run[0]] or script[run[0]]:
                lines.append(run)
            else:
                lines += split_run(g, run, st["line_chars"])
        baseline = st["top"] * k
        for li, idx in enumerate(lines):
            is_script, hot = script[idx[0]], accent[idx[0]]
            text = " ".join(g[j]["word"].lower() if is_script else g[j]["word"].upper() for j in idx)
            family = st["script_font"] if is_script else st["font"]
            if hot:
                w1, _ = text_width(text, family, base)
                size = base * max(st["accent_min"], min(st["accent_max"], st["accent_width"] * width / w1))
            else:
                size = base * (st["script_size"] if is_script else 1.0)
            # базовая линия: строки стоят вплотную, рукописная заходит на капс сверху (как в референсе)
            height = size * (xh_s * 1.9 if is_script else cap_c)
            baseline += height * (1.0 if li == 0 else 1.28 if not is_script else 0.92)
            asc = size * (asc_s if is_script else asc_c)
            line_w, _ = text_width(text, family, size)
            off = 0 if hot else offsets[n % len(offsets)]
            n += 0 if hot else 1
            x = min(max(width / 2 + off * width - line_w / 2, 30 * k), width - line_w - 30 * k)
            y = baseline - asc
            face = f"\\fn{family}\\fs{round(size)}"
            t0 = g[idx[0]]["start"]
            if hot:
                letters, cx = [], x
                for ch in text:
                    cw, _ = text_width(ch, family, size)
                    letters.append((ch, cx, cw))
                    cx += cw
                events += fly_in(letters, y, t0 - 0.05, tail, st, width, k, ass_colour(st["hi"]), face)
            else:
                events.append((t0, f"Dialogue: 0,{ass_time(t0)},{ass_time(tail)},Cap,,0,0,,"
                                   f"{{\\an7\\pos({x + ox:.0f},{y + oy:.0f}){face}{shadow}}}{text}"))
                events.append((t0, f"Dialogue: 1,{ass_time(t0)},{ass_time(tail)},Cap,,0,0,,"
                                   f"{{\\an7\\pos({x:.0f},{y:.0f}){face}\\bord0\\shad0\\1c&HFFFFFF&}}{text}"))
    return [e for _, e in sorted(events, key=lambda e: e[0])]


def split_run(g, run, line_chars):
    """Капс длиннее line_chars — на две строки по split_point."""
    words = [g[j]["word"] for j in run]
    if sum(len(w) + 1 for w in words) - 1 <= line_chars or len(run) == 1:
        return [run]
    at = split_point([len(w) for w in words], min_total=line_chars) or 1
    return [run[:at]] + split_run(g, run[at:], line_chars)


def split_point(lengths, min_total=18):
    """Где сломать строку на две ровные половины; None — оставить одной."""
    if sum(lengths) + len(lengths) - 1 <= min_total:
        return None
    best, at = None, None
    for i in range(1, len(lengths)):
        top = sum(lengths[:i]) + i - 1
        bottom = sum(lengths[i:]) + len(lengths) - i - 1
        score = abs(top - bottom) + (100 if lengths[i - 1] <= 2 else 0)   # не оставлять предлог в конце строки
        if best is None or score < best:
            best, at = score, i
    return at


def ass_time(t):
    h, r = divmod(max(t, 0), 3600)
    m, s = divmod(r, 60)
    return f"{int(h):d}:{int(m):02d}:{s:05.2f}"


def captions(words_json, cuts_path, out_ass, style_key="d"):
    cuts = load_cuts(cuts_path)
    st = dict(STYLES[style_key])
    st.update({k: v for k, v in cuts.get("captions", {}).items() if k in st})   # шрифт/размер — из cuts.json
    width, height = cuts["size"]
    k = width / 1080
    items = clean_words(json.load(open(words_json))["words"],
                        DEFAULT_MERGE + cuts.get("merge", []), cuts.get("fix", []))
    opts = cuts.get("captions", {})
    # Whisper выдумывает слова на тишине — окна [от, до] в секундах результата, слова оттуда выкидываем
    items = [w for w in items if not any(a <= w["start"] <= b for a, b in opts.get("drop", []))]
    # подвинуть отдельное слово: [[примерный start, новый start | null, новый end | null], …] в секундах результата —
    # например, показать подпись, когда в кадре уже лицо, а не картинка, и подержать её до склейки
    for near, new_start, new_end in opts.get("retime", []):
        w = min(items, key=lambda x: abs(x["start"] - near))
        if abs(w["start"] - near) > 0.5:
            sys.exit(f"retime: нет слова около {near:.2f} с (ближайшее «{w['word']}» на {w['start']:.2f})")
        if new_start is not None:
            w["start"] = new_start
        if new_end is not None:
            w["end"] = new_end
    # окна говорящих [[от, до, "b"], …] в секундах результата — субтитр не перешагивает смену говорящего
    windows = opts.get("speakers", [])
    cuts_at = sorted(cut_points(cuts) + [t for a, b, _ in windows for t in (a, b)])
    groups = group(items, opts.get("max_chars", st["max_chars"]), cuts_at, max_dur=st.get("max_dur", 2.2),
                   breaks=opts.get("breaks", ()), joins=opts.get("joins", ()))

    # слова, которые рисуются рукописным и строчными («неплохо ПОЛУЧИЛОСЬ») — только у стилей со script
    handwritten = {i + j for seq in opts.get("script", ()) for i in find_seq(items, seq) for j in range(len(seq))}
    # строка-панч — жёлтая целиком; ищем по последовательности слов, иначе «не» подсветит пол-ролика
    accented = {i + j for seq in opts.get("accent", ()) for i in find_seq(items, seq) for j in range(len(seq))}
    at = {id(w): i for i, w in enumerate(items)}
    outline, shadow = st.get("outline", 5), st.get("shadow", 3)

    prepared = []
    for gi, g in enumerate(groups):
        script = [bool(st.get("script_font")) and at[id(w)] in handwritten for w in g]
        accent = [at[id(w)] in accented for w in g]
        tail = g[-1]["end"] + CAPTION_TAIL
        if gi + 1 < len(groups):
            tail = min(tail, groups[gi + 1][0]["start"])   # иначе два субтитра покажутся разом
        else:
            tail = max(tail, g[0]["start"] + 0.25)
        prepared.append((g, script, accent, tail))

    margin_v = round(opts.get("margin_v", st.get("margin_v", CAPTION_MARGIN_V)) * k)
    if st.get("kinetic2"):
        events = kinetic2_events(prepared, st, width, k)
    elif st.get("palette"):
        events = pill_events([(*p, speaker_of(p[0][0]["start"] + 0.05, cuts, windows)) for p in prepared],
                             st, width, height, margin_v, k)
    elif st.get("kinetic"):
        events = kinetic_events(prepared, st, width, k)
    else:
        events = static_events(prepared, st, k)
    header = ASS_HEADER.format(w=width, h=height, font=st["font"], size=round(st["size"] * k),
                               bold=st["bold"], spacing=st["spacing"], outline_c=OUTLINE_C,
                               outline=round(outline * k), shadow=round(shadow * k),
                               margin_lr=round(st.get("margin_lr", 170) * k),
                               margin_v=margin_v)
    Path(out_ass).write_text(header + "\n".join(events) + "\n")
    overlaps = "—" if st.get("kinetic") or st.get("kinetic2") else check_overlaps(out_ass)   # у «f» строки перекрываются по замыслу
    print(f"{len(groups)} субтитров, {len(events)} событий, наложений: {overlaps}", file=sys.stderr)
    print(" ".join(" ".join(w["word"] for w in g) for g in groups))


def check_overlaps(ass_path):
    times = []
    for line in open(ass_path):
        m = re.match(r"Dialogue: 0,([\d:.]+),([\d:.]+),", line)   # слой 1 — текст поверх плашки «g»
        if m:
            to_sec = lambda t: sum(x * float(y) for x, y in zip((3600, 60, 1), t.split(":")))
            times.append((to_sec(m.group(1)), to_sec(m.group(2))))
    return sum(1 for (_, b), (c, _) in zip(times, times[1:]) if b > c + 1e-6)


# ---------------------------------------------------------------- burn

def burn(src, ass_path, out):
    run(["ffmpeg", "-v", "error", "-y", "-i", src, "-vf", f"ass={ass_path}:fontsdir={FONTS_DIR}",
         "-c:v", "libx264", "-preset", "slow", "-crf", os.environ.get("EDIT_CRF", "20"), "-pix_fmt", "yuv420p",
         "-c:a", "copy", "-movflags", "+faststart", out])
    _, _, duration = probe(out)
    print(f"{out}  {duration:.1f} с")


# ---------------------------------------------------------------- frames / onsets / envelope

def frames(out_jpg, cols, specs):
    """Кадры по списку «файл:секунда», подписанные и сложенные в сетку — смотреть стыки и реквизит."""
    cols, tmp = int(cols), []
    for i, spec in enumerate(specs):
        src, t = spec.rsplit(":", 1)
        name = Path(src).stem.replace("IMG_", "")[:10]
        p = Path(out_jpg).with_name(f"_{Path(out_jpg).stem}_{i:02d}.png")
        run(["ffmpeg", "-v", "error", "-y", "-ss", t, "-i", src, "-frames:v", "1", "-vf",
             f"scale=300:-1,drawtext=fontfile={LABEL_FONT}:text='{name} {t}':x=4:y=4:fontsize=20:"
             "fontcolor=yellow:box=1:boxcolor=black@0.7", str(p)])
        tmp.append(p)
    rows = -(-len(tmp) // cols)
    padded = tmp + [tmp[-1]] * (rows * cols - len(tmp))
    layout = []
    for i in range(rows * cols):
        c, r = i % cols, i // cols
        x = "+".join(["0"] + [f"w{j}" for j in range(c)]) if c else "0"
        y = "+".join(["0"] + [f"h{j * cols}" for j in range(r)]) if r else "0"
        layout.append(f"{x}_{y}")
    run(["ffmpeg", "-v", "error", "-y", *[a for p in padded for a in ("-i", str(p))], "-filter_complex",
         f"xstack=inputs={rows * cols}:layout={'|'.join(layout)}", "-frames:v", "1", out_jpg])
    for p in set(tmp):
        p.unlink()
    print(out_jpg)


def onsets(src, start, end, thresh=-32):
    """Отрезки речи в диапазоне (silencedetect) — точные начала фраз; Whisper у тихих слов промахивается на 0.2–0.3 с."""
    r = subprocess.run(["ffmpeg", "-v", "info", "-ss", str(start), "-t", str(end - start), "-i", src, "-af",
                        f"highpass=f=120,silencedetect=n={thresh}dB:d=0.12", "-f", "null", "-"],
                       capture_output=True, text=True).stderr
    spans, cur, speaking = [], start, True
    for kind, t in re.findall(r"silence_(start|end): ([\d.]+)", r):
        t = start + float(t)
        if kind == "start":
            spans.append((cur, t))
            speaking = False
        else:
            cur, speaking = t, True
    if speaking:
        spans.append((cur, end))
    print(f"{Path(src).name} {start}-{end}: " + "  ".join(f"[{a:.2f}-{b:.2f}]" for a, b in spans if b - a > 0.05))


def envelope(src, start, end, step_ms=40):
    """Огибающая RMS по шагу: сравнить ритм фразы в дубле и в меме, найти, где на самом деле кончается слово."""
    n = int(16000 * step_ms / 1000)
    r = subprocess.run(["ffmpeg", "-v", "info", "-ss", str(start), "-t", str(end - start), "-i", src, "-af",
                        f"highpass=f=150,aresample=16000,asetnsamples={n},astats=metadata=1:reset=1,"
                        "ametadata=print:key=lavfi.astats.Overall.RMS_level:file=-", "-f", "null", "-"],
                       capture_output=True, text=True).stdout
    vals = [float(x) for x in re.findall(r"RMS_level=(-?[\d.]+|-inf)", r.replace("-inf", "-99"))]
    peak = max(vals) if vals else 0
    row = "".join("#" if peak - v < 6 else "+" if peak - v < 12 else "-" if peak - v < 20 else "." for v in vals)
    ruler = "".join(f"|{start + i * step_ms / 1000:<9.2f}" for i in range(0, len(vals), 10))
    print(f"{Path(src).name}  пик {peak:.0f} дБ, {step_ms} мс/символ; # до −6, + до −12, - до −20 дБ от пика")
    print(row)
    print(ruler[:len(row)])


def mapwords(cuts_path, out_json):
    """Слова результата, собранные из расшифровок исходников (tx/<имя>.json) по cuts.json — без повторной
    расшифровки результата: Whisper каждый прогон слышит по-разному, а тайминги в tx/ уже проверены.
    Слово относится к куску по своей середине (начало первого слова после паузы Whisper ставит рано)."""
    cuts = load_cuts(cuts_path)
    tx_dir = Path(cuts_path).parent / "tx"
    cache = {}

    def words_of(src):
        if src not in cache:
            path = tx_dir / (Path(src).stem + ".json")
            if not path.exists():
                sys.exit(f"нет расшифровки {path} — сделать: edit.py transcribe {src} {path}")
            cache[src] = json.load(open(path))["words"]
        return cache[src]

    out, t = [], 0.0
    for seg in cuts["segments"]:
        start, end, speed, src, _ = segment_fields(seg, cuts)
        dur = (end - start) / speed
        audio = seg.get("audio") if isinstance(seg, dict) else None
        if audio:
            a_start = audio["start"]
            src, start, speed = os.path.expanduser(audio["src"]), a_start, 1.0
            end = min(audio.get("end", a_start + dur), a_start + dur)
        for w in words_of(src):
            mid = (w["start"] + w["end"]) / 2
            if start <= mid < end:
                out.append({"word": w["word"],
                            "start": round(max(t, t + (w["start"] - start) / speed), 2),
                            "end": round(min(t + dur, t + (w["end"] - start) / speed), 2)})
        t += dur
    json.dump({"words": out, "duration": round(t, 2)}, open(out_json, "w"), ensure_ascii=False, indent=1)
    print(f"{len(out)} слов, {t:.1f} с", file=sys.stderr)


def denoise(src, out, atten=14):
    """ИИ-шумодав DeepFilterNet (ставится ./install.sh denoise) — копия исходника
    с очищенным звуком, видео не перекодируется. atten — предел подавления, дБ: без него (или выше ~20)
    модель глотает тихие слова дальнего голоса («бахнуть» пропало); 14 — шум тише, слова на месте.
    Громкость потом выравнивает "audio_fx": "voice" в cuts.json."""
    import tempfile
    tmp = Path(tempfile.mkdtemp())
    wav = tmp / "in.wav"
    run(["ffmpeg", "-v", "error", "-y", "-i", src, "-vn", "-ac", "1", "-ar", "48000", str(wav)])
    df = shutil.which("deepFilter") or str(Path(sys.executable).parent / "deepFilter")
    run([df, "--atten-lim", str(atten), str(wav), "-o", str(tmp / "out")], capture_output=True)
    clean = next((tmp / "out").glob("*.wav"))
    run(["ffmpeg", "-v", "error", "-y", "-i", src, "-i", str(clean), "-map", "0:v", "-map", "1:a",
         "-c:v", "copy", "-c:a", "aac", "-b:a", "256k", "-map_metadata", "0", out])
    shutil.rmtree(tmp)
    print(out)


def facetrack(src, start, end, step=0.3):
    """Ключевые точки лица для "zoom": {"track": …}: кадры 10 к/с → детектор macOS Vision (tools/facedetect.swift,
    собирается сам) → сглаживание ±0.15 с → точки через step секунд. Печатает JSON [[секунда, cx, cy], …];
    где лица не видно (отвернулась), точек нет — между соседними окно едет линейно."""
    import tempfile
    tool = Path(__file__).with_name("facedetect")
    swift = tool.with_suffix(".swift")
    if not tool.exists() or tool.stat().st_mtime < swift.stat().st_mtime:
        run(["swiftc", "-O", "-o", str(tool), str(swift)])
    tmp = Path(tempfile.mkdtemp())
    run(["ffmpeg", "-v", "error", "-y", "-ss", str(start), "-t", str(end - start), "-i", src,
         "-vf", "fps=10,scale=540:-1", "-start_number", "0", str(tmp / "f_%04d.jpg")])
    files = sorted(tmp.glob("f_*.jpg"))
    out = run([str(tool), *map(str, files)], capture_output=True, text=True).stdout
    det = {}
    for line in out.splitlines():
        parts = line.split()
        if len(parts) >= 3 and parts[1] != "-":
            det[round(start + int(parts[0][2:6]) / 10, 2)] = (float(parts[1]), float(parts[2]))
    for f in files:
        f.unlink()
    tmp.rmdir()
    keys, t = [], start
    while t <= end + 1e-6:
        near = [det[k] for k in det if abs(k - t) <= 0.15]
        if near:
            keys.append([round(t, 2), round(sum(c for c, _ in near) / len(near), 3),
                         round(sum(c for _, c in near) / len(near), 3)])
        t += step
    print(f"{len(det)} кадров с лицом из {len(files)}, {len(keys)} точек", file=sys.stderr)
    print(json.dumps(keys))


# ---------------------------------------------------------------- cli

COMMANDS = {
    "transcribe": lambda a: transcribe(a[0], a[1], a[2] if len(a) > 2 else "local"),
    "words": lambda a: words(a[0], float(a[1]), float(a[2])),
    "sheet": lambda a: sheet(a[0], a[1], int(a[2]) if len(a) > 2 else 5),
    "render": lambda a: render(a[0], a[1]),
    "normalize": lambda a: normalize(a[0], a[1]),
    "mapwords": lambda a: mapwords(a[0], a[1]),
    "captions": lambda a: captions(a[0], a[1], a[2], a[3] if len(a) > 3 else "d"),
    "burn": lambda a: burn(a[0], a[1], a[2]),
    "frames": lambda a: frames(a[0], a[1], a[2:]),
    "denoise": lambda a: denoise(a[0], a[1], *(float(x) for x in a[2:3])),
    "onsets": lambda a: onsets(a[0], float(a[1]), float(a[2]), float(a[3]) if len(a) > 3 else -32),
    "envelope": lambda a: envelope(a[0], float(a[1]), float(a[2]), int(a[3]) if len(a) > 3 else 40),
    "facetrack": lambda a: facetrack(a[0], float(a[1]), float(a[2]), float(a[3]) if len(a) > 3 else 0.3),
}

if __name__ == "__main__":
    if len(sys.argv) < 2 or sys.argv[1] not in COMMANDS:
        sys.exit(__doc__)
    try:
        COMMANDS[sys.argv[1]](sys.argv[2:])
    except IndexError:
        sys.exit(__doc__)
