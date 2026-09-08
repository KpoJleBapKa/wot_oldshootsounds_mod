# OldShootSounds for World of Tanks

Мод повертає звуки пострілів із WoT 1.29.1.1 лише машинам і гарматам, які були в цій версії. Нові машини та нові гармати WoT 2.x не змінюються.

Готовий архів: `dist/OldShootSounds.zip`.

## Встановлення

Розпакувати архів і запустити подвійним кліком:

    Install-OldShootSounds.cmd

Відкриється стандартне вікно вибору папки. Потрібно вказати кореневу папку World of Tanks — ту, де лежать `paths.xml`, `res` і `res_mods`.

За потреби інсталятор також можна запустити з PowerShell:

```powershell
powershell -NoProfile -ExecutionPolicy Bypass -File .\Install-OldShootSounds.ps1 -GameRoot "W:\World_of_Tanks_EU"
```

Інсталятор читає активну версію `res_mods` із `paths.xml`, копіює банк та Python-мод, а потім додає `oldshoot.bnk` до наявного `audio_mods.xml`. Перед першою зміною створюється `audio_mods.xml.oldshoot.bak`. `voiceover.bnk` та записи інших модпаків не перезаписуються.

## Перевірка звуків в ангарі

Натискайте `F8` в ангарі. Кожне натискання програє наступну з 22 подій: вісім основних категорій і три категорії двоствольного залпу спочатку для власної машини, а потім для інших машин. Після останньої події список починається спочатку. Поточна назва події показується в системному повідомленні та записується в `game.log`.

Перед запуском наступної події мод зупиняє попередню, тому довгі звуки пострілів не накладаються один на одного.

Поза ангаром тестова клавіша не працює. Вона перевіряє завантаження банку, події та аудіофайли; просторове позиціювання звуку потрібно перевіряти реплеєм або в бою.

## Збирання

Побудова точної мапи машин і гармат:

```powershell
python tools\build_old_gun_whitelist.py
```

Підготовка старих звуків:

```powershell
python tools\prepare_old_event_audio.py --variants 4
```

Побудова Wwise-банку:

```powershell
python tools\build_wwise_bank.py --wwise-console "F:\!myprojects\app_for_development\Wwise_2023.1.8.8601\Authoring\x64\Release\bin\WwiseConsole.exe"
```

Побудова релізу:

```powershell
python tools\build_release.py --python2 "reference\WotSourceExtractor\tools\python2\python.exe"
```

Перевірка:

```powershell
python tools\validate_release.py
```
