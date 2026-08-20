import os

filepath = os.path.join(os.path.dirname(__file__), "..", "..", "sample_models", "P-796-ULT-V22.3-UPDATED-01-06-2026.$et")
with open(filepath, "r", encoding="utf-8", errors="ignore") as f:
    for line in f:
        stripped = line.strip()
        if stripped.startswith("$ "):
            print(stripped)
