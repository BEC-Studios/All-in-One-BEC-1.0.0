import os

BASE = os.path.abspath(os.path.join(os.path.dirname(__file__), ".."))
PLUGINS = os.path.join(BASE, "plugins")
BETTER = os.path.join(BASE, "BetterEditPMF")
TARGET = os.path.join(PLUGINS, "BetterEditPMF_loader.py")

LOADER_CODE = r'''# plugins/BetterEditPMF_loader.py
# Auto-generated loader for BetterEditPMF
import os, sys

BASE = os.path.abspath(os.path.join(os.path.dirname(__file__), ".."))
BETTER = os.path.join(BASE, "BetterEditPMF")
if BETTER not in sys.path:
    sys.path.insert(0, BETTER)

from ai1cmd_pack import register  # noqa
'''

def main():
    os.makedirs(PLUGINS, exist_ok=True)
    with open(TARGET, "w", encoding="utf-8") as f:
        f.write(LOADER_CODE)
    print("[OK] Installed plugin loader:", TARGET)
    print("Now start AI1 and run in Terminal: plugins")

if __name__ == "__main__":
    main()
