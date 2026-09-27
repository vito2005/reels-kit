# Звуки для монтажа

`memes/` — пак «viral memes sfx» (Google Drive, 159 файлов), скачан 25.09.2026.
Происхождение и лицензии неизвестны: это сборник из интернета. Музыка Kevin MacLeod — CC-BY, нужна подпись
«Kevin MacLeod (incompetech.com)». Фразы из фильмов и сериалов — чужие права: короткие куски в скетчах обычно
проходят, но Instagram может заглушить звук.

Поиск по описанию (CLAP, локально): `python3 tools/sfxtag.py search sfx/ "whoosh transition" 5`.
Запросы лучше писать по-английски и называть сам звук («cartoon boing»), а не смысл («сюрприз»): смысл модель
понимает плохо. Метки топ-3 для каждого файла лежат в `tags.json`, после добавления звуков — `sfxtag.py index sfx/`.
В ролик звук ставится через `"sfx"` у куска в `cuts.json` (см. шапку `tools/edit.py`).

Ниже `memes/Memes-Comedy/SFX_<имя>` сгруппированы по назначению. Разбирал по именам файлов, Whisper (речь)
и CLAP (метки). Ушами не слушал. Безымянные `Funny-Effect-*` и `Most-Used-Effects-*` описаны по меткам CLAP.

## Переходы, зум, смена плана (вжухи)
`Whoosh`, `Swish5` (0.3 с, самый короткий), `High-Fast-Swoosh` (0.6 с), `Golden-Swoosh`, `Thick-Wipe`,
`Thick-Wipe-Phazed`, `Low-Fly`, `Space-Woosh`, `Space-Ship-Fly-By`, `Space-Ship-Woosh`, `Stutter-Fly-By`,
`Cinematic-Whoosh`, `Static-Swoosh`, `Slow-Reverb-Swoosh`, `Stutter-Swish`, `Stutter-Woosh`, `Speed-Swoosh` (9.7 с, резать),
`Gas-Fire-Swoosh`, `Torpedo`, `Most-Used-Effects-2`.
Как применять: `at` ≈ −0.2…−0.3, чтобы пик вжуха пришёлся на склейку или начало быстрого зума.

## Нагнетание перед панчем
`Drum-Roll`, `Drumroll`, `Long-Suspense-1…4`, `Suspense`, `Suspense-2`, `Suspense-3`, `Panic-Suspense`, `Heart-Beat`,
`Reverse-Riser-03-Nice`, `Reverse-Riser-04-Train` (обратный райзер: конец звука ставить на панч), `Scary-High-Zing`,
`Dun-Dun-Dun`, `Dun-Dun-Dun-2` (драматичное «та-да-дам»), `Run`.

## Удар, панч, «бум»
`Shocked-Hd`, `Deep-Cinematic-Bass-Drum-Impact`, `Bass-Boosted`, `Explosion`, `Punch`, `Punch-1`, `Punch-2`, `Slap`,
`Splat`, `Splat-2`, `Glass-Breaking` (mp3 и wav), `Badum-Tssss` (ба-дум-тсс после шутки).

## Провал, «не получилось»
`Fail-1`, `Fail-2` (грустный тромбон, «ва-ва-ва»), `Wrong-Answer`, `Wrong-Buzzer`, `Denied` («Denied!»), `Sad-Effect`,
`Sad-Romance` (грустная скрипка, 22 с), `Window-Error-Mlg`, `Steve-Death` («уф» из Minecraft), `Falling` (свист падения).

## Успех, «получилось»
`Correct-Answer`, `Ding`, `Ting-1`, `Ting-2`, `Kids-Cheering` («Ура!»), `Kids-Cheering-2`, `Clapping`, `Clapping-Effect`,
`Hallelujah-Chorus`, `Anime-Wow`, `Illuminati` (мистическая тема).

## Реакция «зала»
`Aww`, `Ooohhh`, `Reactioncrowd-Ar02-34-1` («Whoa!»), `Reactioncrowd-Ar04-12-1` («Awww»),
`Reactionchildren-Ar04-79-5` (детское «Wow!»), `Booing-Crowd` (28 с), `Crowd-Booing`, `19312-Kids-Small-Group-Laughing`,
`Funny-Laughing-1…3`, `Troll-Kids`, `Daaamn`.

## Мультяшное: движение, падение, писк
`Ball-Bouncing`, `Cartoon-Accent`, `Cartoon-Running` (убегает), `Rubber-Duck`, `Quack-Sound`, `Derp`, `Bottle-Cork`,
`Drop`, `Drop-1`, `Jump-Super-Mario`, `Waka-Waka-Pakman`, `Rocket-Effect`, `String-Effect`, `Fart-1`, `Fart-2`,
`Funny-Sneeze`, `Funny-Sleeping-Effect` (храп), `Eagle-Sound`,
`Funny-Effect-1` (хлопок-пробка), `-2` (музычка), `-3` (пищалка), `-4` (боинг), `-5` (ба-дум-тсс), `-6` (музычка),
`-7` (пищалка), `-8` (пук/шлепок, 0.5 с), `-9` (слайд-свисток), `-10` (боинг), `Most-Used-Effects-1` (кряк),
`-3` (бег), `-4` (боинг).

## Бытовые звуки (могут «сыграть» в кадре)
`Alarm-Clock`, `Cell-Phone-Ringing`, `Door-Bell`, `Door-Knocking-Effect`, `School-Bell`, `Car-Horn`, `Horn-1…3`,
`Camera-Shutter`, `Taking-Photos`, `Mouse-Click`, `Censor` (запикать слово),
`Tape-Rewind` (перемотка назад: «а началось всё так»), `Turntable-Scratch` (стоп: «да, это я»), `Flashback`.

## Фразы-мемы (английский)
| файл | что звучит | куда |
|---|---|---|
| `Just-Do-It` | Шайа Лабаф: «Do it! Just…» | мотивирует ребёнка / себя |
| `It-S-Just-A-Prank-Bro` | «It's just a prank, bro» + крики | розыгрыш пошёл не так |
| `Let-S-Get-Ready-To-Rumble` | «Let's get ready to rumble!» | начало битвы: ужин, уборка, укладывание |
| `Look-At-This-Dude` | «Bruh, look at this dude», смех (26 с) | кто-то делает глупость |
| `No-God-Please-No` | Майкл Скотт из «Офиса»: «No, God, please, no!» | ужас от новости |
| `Oh-Hello-There` | Оби-Ван: «Oh, hello there» | кто-то появляется в кадре |
| `Surprise-Mother-Fcker` | Декстер (мат, 18+) | неожиданное появление. В семейные ролики не брать |
| `Wait-A-Minute` | «Wait a minute! Who are you?» | подозрение, узнавание |
| `What-The-Hell` | «What the hell?!» | реакция на абсурд |
| `Why-Are-You-Running` | «Why are you running?» | ребёнок убегает |
| `He-Needs-Some-Milk` | «He needs some milk» | голодный / капризный ребёнок |
| `Yoloo`, `Yeet`, `Aye` | «YOLO!», «Yeet!», «Aye!» | рискованный поступок, бросок |
| `Man-Screaming-1` | крик | паника |
| `Iridocyclitis` | «Iridocyclitis» | мем-фраза, смысл не опознан |

## Музыкальные подложки
Kevin MacLeod (CC-BY): `Fluffing-A-Duck` (дурашливая), `Monkey-Spining-Monkeys` (суета), `Merry-Go` (карусель),
`Investigations` (расследование, «кто съел конфету»). Остальное: `Bit-Happy-Nation_08` (8-бит), `Brodyquest`,
`The-Builder` (стройка, «папа чинит»), `Dip-Dip-Potato-Chip` (тикток), `Jingle-Bells`, `Sad-Romance`.
Подкладывать через `"bed"` с `gain` около −18.

## Для русской аудитории
Невербальное (вжух, бум, тромбон, скретч, «аww», смех) понятно всем. Английские фразы узнают не все, поэтому лучше
брать 2–3 самых известных (`Oh-Hello-There`, `No-God-Please-No`, `Just-Do-It`). Русские мем-звуки есть на zvukogram.com
и promosounds.ru, лицензий там тоже нет.
