import pandas as pd

from analyzer.report import monthly_summary, plot_monthly_spending


def sample_df():
    return pd.DataFrame(
        {
            "date": pd.to_datetime(["2026-05-01", "2026-05-02", "2026-05-03", "2026-06-01"]),
            "amount": [900.0, -20.0, -10.0, -350.0],
            "category": ["Income", "Groceries", "Groceries", "Rent"],
        }
    )


def test_monthly_summary_excludes_income_and_sums_spending():
    s = monthly_summary(sample_df())
    assert "Income" not in s.columns
    assert s.loc["2026-05", "Groceries"] == 30.0
    assert s.loc["2026-06", "Rent"] == 350.0
    assert s.loc["2026-05", "Rent"] == 0


def test_plot_writes_png(tmp_path):
    out = plot_monthly_spending(sample_df(), tmp_path / "chart.png")
    assert out.exists() and out.stat().st_size > 0
