import json

import pytest
from fastapi.testclient import TestClient

from server import create_app

CSV = (
    "Buchungstag;Verwendungszweck;Betrag\n"
    "01.05.2026;GEHALT WERKSTUDENT;900,00\n"
    "03.05.2026;REWE SAGT DANKE;-1.020,50\n"
    "04.05.2026;KIOSK;-3,00\n"
).encode("latin-1")


@pytest.fixture
def client(tmp_path):
    rules = tmp_path / "rules.json"
    rules.write_text(json.dumps({"Groceries": ["REWE"], "Income": ["GEHALT"]}), encoding="utf-8")
    return TestClient(create_app(db_path=tmp_path / "test.db", rules_path=rules))


def upload(client, data=CSV, name="statement.csv"):
    return client.post("/api/import", files={"file": (name, data, "text/csv")})


def test_empty_db_returns_no_transactions(client):
    r = client.get("/api/transactions")
    assert r.status_code == 200
    assert r.json() == []


def test_import_then_list(client):
    r = upload(client)
    assert r.status_code == 200
    assert r.json() == {"filename": "statement.csv", "rows": 3, "new": 3}

    rows = client.get("/api/transactions").json()
    assert [t["category"] for t in rows] == ["Income", "Groceries", "Other"]
    assert rows[1] == {
        "id": 2, "date": "2026-05-03", "description": "REWE SAGT DANKE",
        "amount": -1020.5, "category": "Groceries",
    }


def test_reimport_adds_no_duplicates(client):
    upload(client)
    assert upload(client).json()["new"] == 0
    assert len(client.get("/api/transactions").json()) == 3


def test_bad_csv_is_rejected(client):
    r = upload(client, b"foo;bar\n1;2\n")
    assert r.status_code == 400
    assert "Missing columns" in r.json()["detail"]


def test_categories_include_other_and_colors(client):
    cats = client.get("/api/categories").json()
    assert [c["name"] for c in cats] == ["Groceries", "Income", "Other"]
    assert cats[0]["color"] == "#0072B2"


def test_frontend_is_served(client):
    r = client.get("/")
    assert r.status_code == 200
    assert "<title>" in r.text
