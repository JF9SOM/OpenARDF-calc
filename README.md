# OpenARDF-calc

ARDF (Amateur Radio Direction Finding) competition scoring software.

[日本語版 README](README_ja.md)

## Features

- Competition management for ARDF events
- Competitor data import via CSV
- SI (SportIdent) punch data import from SI Manager CSV
- Ranking calculation and results export
- Japanese / English UI switching

## Requirements

- Python 3.10+
- PySide6 6.6+

## Installation

```bash
git clone https://github.com/JF9SOM/OpenARDF-calc.git
cd OpenARDF-calc
pip install -r requirements.txt
```

## Build Translations

Before running (required for English UI):

```bash
python scripts/build_translations.py
```

## Usage

```bash
python src/main.py
```

## Project Structure

```
src/
  main.py               Entry point
  ui/
    main_window.py      Main window
  core/
    database.py         SQLite database layer
    si_reader/          SI data reader (pluggable)
      base.py           Abstract base class
      si_manager_csv.py SI Manager CSV reader (Phase 1)
  translations/
    en.ts               English translation source
```

## SI Data Import

**Phase 1 (implemented):** Import from SI Manager exported CSV files.  
**Phase 2 (planned):** Direct reading from SI reader hardware via `python-sportident`.

## License

MIT — Copyright (c) 2026 JF9SOM
