"""Keyword-based transaction categorization."""
import json
from pathlib import Path

DEFAULT_RULES_PATH = Path(__file__).resolve().parent.parent / "categories.json"


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
