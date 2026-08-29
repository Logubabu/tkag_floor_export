import sys
import os

# Add root directory and backend directory to sys.path
root_dir = os.path.dirname(os.path.abspath(__file__))
backend_dir = os.path.join(root_dir, "backend")

for p in [root_dir, backend_dir]:
    if p not in sys.path:
        sys.path.insert(0, p)

from gui.app_gui import main

if __name__ == "__main__":
    main()
