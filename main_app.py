import sys
import os
import multiprocessing

# Crucial for PyInstaller frozen executable: prevents spawning multiple instances/windows
multiprocessing.freeze_support()

# Add root directory and backend directory to sys.path
root_dir = os.path.dirname(os.path.abspath(__file__))
backend_dir = os.path.join(root_dir, "backend")

# Suppress Qt font database script fallback warnings on Windows
os.environ["QT_LOGGING_RULES"] = "qt.text.font.db.warning=false;qt.text.font.db=false"

for p in [root_dir, backend_dir]:
    if p not in sys.path:
        sys.path.insert(0, p)

from gui.app_gui import main

if __name__ == "__main__":
    main()
