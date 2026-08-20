import os

filepath = os.path.join(os.path.dirname(__file__), "..", "..", "sample_models", "P-796-ULT-V22.3-UPDATED-01-06-2026.$et")
sections = ["$ STORIES", "$ POINT COORDINATES", "$ LINE CONNECTIVITIES", "$ AREA CONNECTIVITIES", "$ LINE ASSIGNS", "$ AREA ASSIGNS", "$ SLAB PROPERTIES", "$ WALL PROPERTIES"]

current_sec = None
with open(filepath, "r", encoding="utf-8", errors="ignore") as f:
    for line in f:
        stripped = line.strip()
        if stripped.startswith("$ "):
            current_sec = stripped
            print("\n=== SECTION:", current_sec, "===")
            continue
        if current_sec in sections:
            print("  ", stripped[:100])
