import pandas as pd
import pytest

from analyzer.loader import load_statement


def write_csv(path, text):
    path.write_bytes(text.encode("latin-1"))
    return path


def test_parses_german_format(tmp_path):
    csv = write_csv(
        tmp_path / "s.csv",
        "Buchungstag;Verwendungszweck;Betrag\n"
        "01.05.2026;rewe sagt danke;-13,15\n"
        "02.05.2026;GEHALT;1.234,56\n"
        "03.05.2026;MÜLLER DROGERIE;-5,00\n",
    )
    df = load_statement(csv)
    assert list(df.columns) == ["date", "description", "amount"]
    assert df["date"].iloc[0] == pd.Timestamp("2026-05-01")
    assert df["description"].iloc[0] == "REWE SAGT DANKE"  # uppercased
    assert df["amount"].tolist() == [-13.15, 1234.56, -5.0]
    assert df["description"].iloc[2] == "MÜLLER DROGERIE"  # latin-1 umlaut


def test_empty_description_becomes_empty_string(tmp_path):
    csv = write_csv(tmp_path / "s.csv", "Buchungstag;Verwendungszweck;Betrag\n01.05.2026;;-1,00\n")
    assert load_statement(csv)["description"].iloc[0] == ""


def test_missing_columns_raises(tmp_path):
    csv = write_csv(tmp_path / "s.csv", "Datum;Text;Betrag\n01.05.2026;X;-1,00\n")
    with pytest.raises(ValueError, match="Missing columns"):
        load_statement(csv)
