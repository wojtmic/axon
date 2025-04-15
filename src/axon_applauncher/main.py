from . import ui as u
from . import generator as g
from . import config as c
from PyQt6.QtWidgets import QApplication
import sys
import os

# Function
def main():
    # Configs
    c.ensure_exists()
    config, style = c.load()

    # Entries
    entries = g.gen_entries(config)

    # UI
    app = QApplication(sys.argv)
    window = u.AxonWindow(config, entries, style)

    # Flags
    if '--rm-cache' in sys.argv:
        print(f"Removing cache for user request ({c.CACHE_ROOT})")
        os.rmdir(c.CACHE_ROOT)
        c.ensure_exists()

    # Running
    window.show()
    sys.exit(app.exec())

# Standalone run
if __name__ == "__main__":
    main()
