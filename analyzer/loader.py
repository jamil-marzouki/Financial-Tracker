"""Read and clean German bank statement CSVs."""
from pathlib import Path

import pandas as pd

# Map the bank's column names to ours. Adjust here if your bank uses other headers.
COLUMN_MAP = {
    "Buchungstag": "date",
    "Verwendungszweck": "description",
    "Betrag": "amount",
}


def load_statement(path: str | Path) -> pd.DataFrame:
    """Load a German bank CSV and return columns: date, description, amount."""
    df = pd.read_csv(
        path,
        sep=";",
        encoding="latin-1",
        decimal=",",
        thousands=".",
        # Read dates/text as strings: otherwise thousands="." strips the dots
        # from "01.05.2026" and pandas turns it into the number 1052026.
        dtype={"Buchungstag": str, "Verwendungszweck": str},
    )
    df = df.rename(columns=COLUMN_MAP)

    missing = {"date", "description", "amount"} - set(df.columns)
    if missing:
        raise ValueError(
            f"Missing columns {sorted(missing)} in {path}. "
            f"Found: {list(df.columns)}. Adjust COLUMN_MAP in analyzer/loader.py."
        )

    df["date"] = pd.to_datetime(df["date"], format="%d.%m.%Y")
    df["description"] = df["description"].fillna("").astype(str).str.upper()
    df["amount"] = pd.to_numeric(df["amount"]).astype(float)
    return df[["date", "description", "amount"]]
