# OldShootSounds for World of Tanks

## English

OldShootSounds restores gunshot audio from World of Tanks 1.29.1.1 in the current World of Tanks client.

The mod replaces recognized standard gunshots for every vehicle from Tier I through Tier X. It supports the player's vehicle, allied and enemy vehicles, arcade and sniper camera states, spatial positioning, and single- and double-barrel guns. Tier XI vehicles and unknown or special firing systems are left unchanged to prevent missing audio.

Each gunshot is assembled dynamically from independently randomized historical sound layers, preserving the natural variation of the original audio instead of repeating a small set of complete recordings.

The mod changes gunshots only. It does not replace engines, tracks, impacts, penetrations, ricochets, shell flybys, reloads, UI, crew voices, music, ambience, destruction, or artillery explosions.

Current version: `1.1`.

### Installation

1. Close World of Tanks.
2. Extract `OldShootSounds-<version>.zip`.
3. Double-click `Install-OldShootSounds.cmd`.
4. Select the World of Tanks root folder containing `paths.xml`, `res`, and `res_mods`.
5. Start the game.

The installer automatically detects the active game version and preserves existing audio mods, including crew voiceovers and entries created by modpacks. Before changing the audio mod list for the first time, it creates an `audio_mods.xml.oldshoot.bak` backup.

After a game update, run the installer again. World of Tanks creates a new version directory and stops loading the previous one, so removing files from an obsolete version directory is normally unnecessary.

### Removal from the active game version

Close the game and remove these files from the active `res_mods/<version>` directory:

```text
audioww/oldshoot.bnk
scripts/client/gui/mods/mod_oldshoot.pyc
scripts/client/gui/mods/oldshoot_data.pyc
```

Then remove only the `<bank>` element containing `<name>oldshoot.bnk</name>` from `audioww/audio_mods.xml`. Restore `audio_mods.xml.oldshoot.bak` only if no other installer has changed `audio_mods.xml` since OldShootSounds was installed.

### Hangar sound test

Press `F8` in the hangar to play the next event in a sequence of 22 sounds:

1. Eight standard player-vehicle categories.
2. Three double-barrel player-vehicle categories.
3. Eight standard allied/enemy categories.
4. Three double-barrel allied/enemy categories.

Wait approximately 3–5 seconds between presses. Sounds are not forcibly stopped and may overlap if the key is pressed rapidly. After sound 22, the sequence starts again. The sound name and position are shown as a system message and written to `game.log`.

`F8` testing is disabled outside the hangar. It verifies that the mod is installed and its sounds can be played. Spatial positioning and vehicle assignment must be tested in a replay or battle.

### Compatibility and safety

- Vehicles and guns that existed in 1.29.1.1 use their corresponding historical gunshot category.
- Newer Tier I–X vehicles use an old sound only when their gun belongs to a supported standard category.
- Tier XI vehicles and unusual or special firing systems keep their current sounds.
- The installer preserves other entries in the audio mod list.
- Another sound mod that replaces the same gunshots may conflict depending on loading order.
- Separately installed crew voiceovers are unaffected and are not included with OldShootSounds.

## Українська

OldShootSounds повертає звуки пострілів із World of Tanks 1.29.1.1 в актуальний клієнт World of Tanks.

Мод замінює розпізнані стандартні звуки пострілів для всіх машин від I до X рівня. Підтримуються власна машина, союзники та противники, аркадний і снайперський режими камери, просторове позиціювання, звичайні та двоствольні гармати. Машини XI рівня, а також невідомі чи спеціальні системи стрільби залишаються без змін, щоб не спричинити зникнення звуку.

Кожен постріл динамічно складається з незалежно рандомізованих історичних звукових шарів, тому мод зберігає природну варіативність оригіналу замість повторення невеликого набору готових записів.

Мод змінює лише постріли гармат. Він не замінює двигуни, гусениці, влучання, пробиття, рикошети, проліт снаряда, перезаряджання, інтерфейс, голоси екіпажу, музику, оточення, руйнування чи вибухи артилерії.

Поточна версія: `1.1`.

### Встановлення

1. Закрийте World of Tanks.
2. Розпакуйте `OldShootSounds-<версія>.zip`.
3. Запустіть подвійним кліком `Install-OldShootSounds.cmd`.
4. Виберіть кореневу папку World of Tanks, у якій знаходяться `paths.xml`, `res` і `res_mods`.
5. Запустіть гру.

Інсталятор автоматично визначає активну версію гри та зберігає наявні звукові моди, включно з озвученням екіпажу і записами модпаків. Перед першою зміною списку звукових модів створюється резервна копія `audio_mods.xml.oldshoot.bak`.

Після оновлення гри запустіть інсталятор повторно. World of Tanks створює нову версійну папку та припиняє завантажувати попередню, тому видаляти мод зі старої неактивної папки зазвичай немає потреби.

### Видалення з активної версії гри

Закрийте гру та видаліть такі файли з активної папки `res_mods/<version>`:

```text
audioww/oldshoot.bnk
scripts/client/gui/mods/mod_oldshoot.pyc
scripts/client/gui/mods/oldshoot_data.pyc
```

Після цього видаліть з `audioww/audio_mods.xml` лише елемент `<bank>`, який містить `<name>oldshoot.bnk</name>`. Відновлюйте `audio_mods.xml.oldshoot.bak` тільки якщо після встановлення OldShootSounds жоден інший інсталятор не змінював `audio_mods.xml`.

### Перевірка звуків в ангарі

Натискайте `F8` в ангарі, щоб послідовно програти 22 звуки:

1. Вісім стандартних категорій власної машини.
2. Три двоствольні категорії власної машини.
3. Вісім стандартних категорій союзників і противників.
4. Три двоствольні категорії союзників і противників.

Між натисканнями зачекайте приблизно 3–5 секунд. Звуки примусово не зупиняються, тому при швидких натисканнях вони можуть накладатися. Після звуку №22 послідовність починається знову. Назва й номер звуку показуються системним повідомленням і записуються в `game.log`.

Поза ангаром тестування через `F8` вимкнене. Воно перевіряє, що мод установлений і його звуки відтворюються. Просторове позиціювання і призначення конкретним машинам потрібно перевіряти в реплеї або бою.

### Сумісність і безпека

- Машини й гармати, які існували у версії 1.29.1.1, використовують відповідну історичну категорію пострілу.
- Новіші машини I–X рівнів отримують старий звук лише тоді, коли їхня гармата належить до підтримуваної стандартної категорії.
- Машини XI рівня та незвичайні або спеціальні системи стрільби зберігають актуальні звуки.
- Інсталятор зберігає інші записи у списку звукових модів.
- Інший звуковий мод, який замінює ті самі постріли, може конфліктувати залежно від порядку завантаження.
- Окремо встановлене озвучення екіпажу не змінюється і не входить до складу OldShootSounds.
