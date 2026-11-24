import pandas as pd

from analyzer.db import init_db, insert_transactions, load_all, monthly_totals


def sample_df():
    return pd.DataFrame(
        {
            "date": pd.to_datetime(["2026-05-01", "2026-05-03", "2026-06-01"]),
            "description": ["GEHALT", "REWE", "MIETE"],
            "amount": [900.0, -20.5, -350.0],
            "category": ["Income", "Groceries", "Rent"],
        }
    )


def test_insert_and_load(tmp_path):
    db = tmp_path / "test.db"
    init_db(db)
    assert insert_transactions(sample_df(), db) == 3
    df = load_all(db)
    assert len(df) == 3
    assert df["date"].dtype.kind == "M"
    assert df["amount"].sum() == 529.5


def test_no_duplicates_on_reimport(tmp_path):
    db = tmp_path / "test.db"
    init_db(db)
    insert_transactions(sample_df(), db)
    assert insert_transactions(sample_df(), db) == 0
    assert len(load_all(db)) == 3


def test_monthly_totals(tmp_path):
    db = tmp_path / "test.db"
    init_db(db)
    insert_transactions(sample_df(), db)
    m = monthly_totals(db).set_index("month")
    assert m.loc["2026-05"].to_dict() == {"income": 900.0, "spent": 20.5, "net": 879.5}
    assert m.loc["2026-06"].to_dict() == {"income": 0.0, "spent": 350.0, "net": -350.0}


def test_empty_db(tmp_path):
    db = tmp_path / "test.db"
    init_db(db)
    assert load_all(db).empty
    assert monthly_totals(db).empty
