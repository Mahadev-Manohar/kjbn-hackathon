"""Run the test suite with coverage and write the committed summary to coverage.txt.

Run from the backend directory:
    python -m scripts.coverage_report

Needs the compose database (docker compose up -d db), like the API tests.
"""

import subprocess
import sys
from pathlib import Path

BACKEND_DIR = Path(__file__).resolve().parents[1]
OUTPUT = BACKEND_DIR / "coverage.txt"

# The business-rules layer: pure rules, no HTTP or database.
RULES_LAYER = "app/domain/*"


def run(*args: str) -> subprocess.CompletedProcess:
    return subprocess.run(
        [sys.executable, "-m", *args], cwd=BACKEND_DIR, capture_output=True, text=True
    )


def main() -> int:
    tests = run("pytest", "-q", "--cov=app", "--cov-report=", "-p", "no:cacheprovider")
    summary = tests.stdout.strip().splitlines()[-1] if tests.stdout.strip() else "no output"
    overall = run("coverage", "report", "--show-missing")
    rules = run("coverage", "report", f"--include={RULES_LAYER}", "--show-missing")
    OUTPUT.write_text(
        f"Test run: {summary}\n\n"
        f"== Overall (app/) ==\n{overall.stdout}\n"
        f"== Business-rules layer ({RULES_LAYER}) ==\n{rules.stdout}",
        encoding="utf-8",
    )
    print(OUTPUT.read_text(encoding="utf-8"))
    return tests.returncode


if __name__ == "__main__":
    raise SystemExit(main())
