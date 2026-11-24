"""Monthly summary and a static matplotlib chart."""
from pathlib import Path

import matplotlib

matplotlib.use("Agg")  # no GUI needed
import matplotlib.pyplot as plt
import pandas as pd


def monthly_summary(df: pd.DataFrame) -> pd.DataFrame:
    """Spending per month and category (expenses as positive numbers, Income excluded)."""
    spend = df[(df["amount"] < 0) & (df["category"] != "Income")].copy()
    spend["month"] = spend["date"].dt.strftime("%Y-%m")
    spend["spent"] = -spend["amount"]
    return spend.pivot_table(
        index="month", columns="category", values="spent", aggfunc="sum", fill_value=0
    ).round(2)


def plot_monthly_spending(df: pd.DataFrame, out_path: str | Path) -> Path:
    summary = monthly_summary(df)
    fig, ax = plt.subplots(figsize=(10, 5))
    summary.plot(kind="bar", stacked=True, ax=ax, edgecolor="white", linewidth=1)
    ax.set_title("Spending per month by category")
    ax.set_xlabel("")
    ax.set_ylabel("€")
    ax.spines[["top", "right"]].set_visible(False)
    ax.legend(frameon=False, bbox_to_anchor=(1.02, 1), loc="upper left")
    fig.tight_layout()
    out_path = Path(out_path)
    fig.savefig(out_path, dpi=120)
    plt.close(fig)
    return out_path
