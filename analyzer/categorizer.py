"""Keyword-based transaction categorization."""
import json
from pathlib import Path

DEFAULT_RULES_PATH = Path(__file__).resolve().parent.parent / "categories.json"

# Fixed colors (Okabe-Ito, colorblind-safe) so a category keeps its color under any filter.
# Shared by the Streamlit dashboard and the web app.
CATEGORY_COLORS = {
    "Groceries": "#0072B2",
    "Transport": "#E69F00",
    "Rent": "#009E73",
    "Online": "#CC79A7",
    "Food": "#56B4E9",
    "Subscriptions": "#D55E00",
    "Income": "#F0E442",
    "Other": "#999999",
}


def load_rules(path: str | Path = DEFAULT_RULES_PATH) -> dict[str, list[str]]:
    with open(path, encoding="utf-8") as f:
        return json.load(f)


def categorize(description: str, rules: dict[str, list[str]]) -> str:
    """Return the first category whose keyword appears in the description, else 'Other'."""
    text = (description or "").upper()
    for category, keywords in rules.items():
        for keyword in keywords:
            if keyword.upper() in text:
                return category
    return "Other"
