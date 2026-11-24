"""CSV -> categorize -> SQLite -> print summary.

Usage: python main.py [path/to/statement.csv]
"""
import sys
from pathlib import Path

import pandas as pd

from analyzer.categorizer import categorize, load_rules
from analyzer.db import init_db, insert_transactions, load_all, monthly_totals
from analyzer.loader import load_statement

DEFAULT_CSV = Path(__file__).resolve().parent / "data" / "fake_statement.csv"


def main() -> None:
    csv_path = Path(sys.argv[1]) if len(sys.argv) > 1 else DEFAULT_CSV
    if not csv_path.exists():
        sys.exit(f"File not found: {csv_path}\nRun: python scripts/generate_fake_data.py")

    init_db()
    df = load_statement(csv_path)
    rules = load_rules()
    df["category"] = df["description"].apply(lambda d: categorize(d, rules))

    new_rows = insert_transactions(df)
    print(f"Imported {csv_path.name}: {new_rows} new transactions ({len(df)} in file)\n")

    pd.set_option("display.width", 120)
    print("Monthly totals (EUR):")
    print(monthly_totals().to_string(index=False))

    other = load_all().query("category == 'Other'").head(10)
    print(f"\nUncategorized ('Other'): {len(other)} shown")
    if not other.empty:
        print(other[["date", "description", "amount"]].to_string(index=False))


if __name__ == "__main__":
    main()
