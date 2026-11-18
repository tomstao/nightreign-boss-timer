"""What the packaged program starts with. PyInstaller builds the executable from this file."""

import sys

from nightreign_boss_timer.ui.app import main

if __name__ == "__main__":
    sys.exit(main())
