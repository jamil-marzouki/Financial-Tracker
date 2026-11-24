"""End-to-end: CSV -> categorize -> SQLite, on a temporary database."""
import analyzer.db as db
from analyzer.categorizer import categorize, load_rules
from analyzer.loader import load_statement


def test_pipeline_on_fake_statement(tmp_path):
    from pathlib import Path

    csv = Path(__file__).resolve().parent.parent / "data" / "fake_statement.csv"
    dbfile = tmp_path / "e2e.db"
    db.init_db(dbfile)
    df = load_statement(csv)
    rules = load_rules()
    df["category"] = df["description"].apply(lambda d: categorize(d, rules))
    assert db.insert_transactions(df, dbfile) == len(df.drop_duplicates())
    stored = db.load_all(dbfile)
    assert (stored["category"] == "Other").sum() == 0  # all fake merchants are covered
    assert len(db.monthly_totals(dbfile)) == 6
