"""Build .qm translation files from .ts source files.

Usage:
    python scripts/build_translations.py
"""
import subprocess
import sys
from pathlib import Path

TRANSLATIONS_DIR = Path(__file__).parent.parent / "src" / "translations"


def build():
    ts_files = sorted(TRANSLATIONS_DIR.glob("*.ts"))
    if not ts_files:
        print("No .ts files found in", TRANSLATIONS_DIR)
        return

    ok = 0
    for ts_file in ts_files:
        qm_file = ts_file.with_suffix(".qm")
        result = subprocess.run(
            ["pyside6-lrelease", str(ts_file), "-qm", str(qm_file)],
            capture_output=True,
            text=True,
        )
        if result.returncode == 0:
            print(f"  Built: {qm_file.name}")
            ok += 1
        else:
            print(f"  ERROR building {ts_file.name}:")
            print(result.stderr or result.stdout)

    print(f"\n{ok}/{len(ts_files)} file(s) built successfully.")


if __name__ == "__main__":
    build()
