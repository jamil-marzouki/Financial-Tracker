from analyzer.categorizer import categorize, load_rules

RULES = {"Groceries": ["REWE", "LIDL"], "Online": ["AMAZON", "PAYPAL"]}


def test_matches_keyword():
    assert categorize("REWE SAGT DANKE", RULES) == "Groceries"


def test_case_insensitive():
    assert categorize("amazon eu s.a r.l.", RULES) == "Online"


def test_first_matching_category_wins():
    assert categorize("LIDL VIA PAYPAL", RULES) == "Groceries"


def test_no_match_is_other():
    assert categorize("UNBEKANNT", RULES) == "Other"


def test_empty_or_none_description():
    assert categorize("", RULES) == "Other"
    assert categorize(None, RULES) == "Other"


def test_default_rules_file_loads():
    rules = load_rules()
    assert "Groceries" in rules and all(isinstance(v, list) for v in rules.values())
