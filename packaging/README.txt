Nightreign Boss Timer
=====================

Records how long each boss fight takes in ELDEN RING NIGHTREIGN by reading the boss health bar
from the screen.

To start
--------
1. Keep all the files in this folder together. Do not run the program from inside the ZIP.
2. Set the game to windowed or borderless windowed mode.
3. Run nightreign-boss-timer.exe. An icon appears in the system tray, near the clock, and a
   short setup guide opens the first time.

Windows may show a SmartScreen warning because the program is not signed. Choose "More info",
then "Run anyway". Only do this for a ZIP downloaded from the project's Releases page.

Where things are kept
---------------------
Records    Documents\nightreign-boss-timer\records.csv  (opens in Excel)
Settings   %APPDATA%\nightreign-boss-timer\settings.json
Log        %LOCALAPPDATA%\nightreign-boss-timer\logs\app.log

To update, quit the program from its tray icon and replace this folder with the new one.
To uninstall, quit the program and delete this folder. Your records and settings are not in it.

Full guide, source code and problem reports
-------------------------------------------
https://github.com/sunfish-LittleKight/nightreign-boss-timer

Safety
------
The program only looks at screen pixels. It does not read game memory, inject code, or change
game files. No third-party tool can be guaranteed safe with anti-cheat software, so you use it
at your own risk. It is not affiliated with FromSoftware or Bandai Namco.

Licences
--------
This program is under the MIT licence: see LICENSE. It contains other open-source software and
a text recognition model: see THIRD_PARTY_NOTICES.md and the licenses folder.
