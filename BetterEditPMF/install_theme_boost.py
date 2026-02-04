# BetterEditPMF/install_theme_boost.py
# Put into: All in One 1.0.0/BetterEditPMF/install_theme_boost.py
# Run (PowerShell):
#   cd "C:\Users\lrazy\Documents\All in One 1.0.0\BetterEditPMF"
#   python install_theme_boost.py
#
# This creates: All in One 1.0.0/plugins/BetterEditPMF_theme_boost_loader.py

import os

BASE = os.path.abspath(os.path.join(os.path.dirname(__file__), ".."))
PLUGINS = os.path.join(BASE, "plugins")
BETTER = os.path.join(BASE, "BetterEditPMF")
TARGET = os.path.join(PLUGINS, "BetterEditPMF_theme_boost_loader.py")

LOADER = r'''# plugins/BetterEditPMF_theme_boost_loader.py
import os, sys

BASE = os.path.abspath(os.path.join(os.path.dirname(__file__), ".."))
BETTER = os.path.join(BASE, "BetterEditPMF")
if BETTER not in sys.path:
    sys.path.insert(0, BETTER)

from bec_theme_boost import register  # noqa
'''

def main():
    os.makedirs(PLUGINS, exist_ok=True)
    with open(TARGET, "w", encoding="utf-8") as f:
        f.write(LOADER)
    print("[OK] Installed loader:", TARGET)
    print("Start AI1 -> in AI1 terminal run: plugins")
    print("Then try: theme apply macos26-glass")

if __name__ == "__main__":
    main()
