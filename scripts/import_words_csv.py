"""
Merge words and tags from a CSV file into the database.

Usage (from repo root, venv active):
  python scripts/import_words_csv.py path/to/data.csv

CSV format: header row with columns word,tag (see API docs). UTF-8 with or without BOM.
"""

from __future__ import annotations

import argparse
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))


def main() -> None:
    parser = argparse.ArgumentParser(description="Import word/tag rows from CSV")
    parser.add_argument("csv_path", type=Path, help="Path to .csv file")
    args = parser.parse_args()
    path: Path = args.csv_path
    if not path.is_file():
        print(f"Not a file: {path}", file=sys.stderr)
        sys.exit(1)

    text = path.read_text(encoding="utf-8-sig")

    from app.csv_import import import_words_tags_csv
    from app.database import SessionLocal

    with SessionLocal() as session:
        result = import_words_tags_csv(session, text)
        if result.row_errors:
            err0 = result.row_errors[0]
            if err0.startswith("CSV has no header") or err0.startswith("CSV must include"):
                print("Fatal:", result.row_errors, file=sys.stderr)
                sys.exit(1)
        session.commit()

    print(
        f"rows_read={result.rows_read} skipped_empty={result.rows_skipped_empty} "
        f"unique_words_created={result.unique_words_created} "
        f"unique_tags_created={result.unique_tags_created} "
        f"links_added={result.links_added} links_already_present={result.links_already_present}"
    )
    if result.row_errors:
        print("Row warnings/errors:", file=sys.stderr)
        for e in result.row_errors:
            print(" ", e, file=sys.stderr)


if __name__ == "__main__":
    main()
