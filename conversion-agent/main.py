import os
import sys
import argparse
import logging

AGENT_DIR = os.path.dirname(os.path.abspath(__file__))
REPO_ROOT = os.path.abspath(os.path.join(AGENT_DIR, ".."))
BACKEND_DIR = os.path.join(REPO_ROOT, "backend")

for p in [AGENT_DIR, REPO_ROOT, BACKEND_DIR]:
    if p not in sys.path:
        sys.path.insert(0, p)

try:
    from conversion.pipeline import ConversionPipeline
except ModuleNotFoundError:
    from conversionagent.conversion.pipeline import ConversionPipeline

def main():
    parser = argparse.ArgumentParser(description="Windows Conversion Agent for ETABS to RAM Concept")
    parser.add_argument("--input", required=True, help="Path to ETABS .EDB or .E2K file")
    parser.add_argument("--story", required=True, help="Story name to extract (e.g. 'Level 05')")
    parser.add_argument("--output", required=True, help="Output .CPT file path")
    
    args = parser.parse_args()

    pipeline = ConversionPipeline()
    res = pipeline.run_conversion(args.input, args.story, args.output)

    print("\n================ CONVERSION SUMMARY ================")
    print(f"Status: {'SUCCESS' if res['success'] else 'FAILED'}")
    print(f"Story: {res['story_name']}")
    print(f"Output File: {res['output_file']}")
    print(f"Duration: {res.get('elapsed_seconds', 0)}s")
    print("\n--- Pipeline Logs ---")
    for log_line in res.get("logs", []):
        print(log_line)

if __name__ == "__main__":
    main()
