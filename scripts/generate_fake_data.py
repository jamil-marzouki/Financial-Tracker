"""Generate a fake German bank statement (data/fake_statement.csv)."""
import csv
import random
from datetime import date, timedelta
from pathlib import Path

OUT = Path(__file__).resolve().parent.parent / "data" / "fake_statement.csv"

START = date(2026, 5, 1)
END = date(2026, 10, 31)  # ~6 months

# merchant -> (min, max) cost in €
MERCHANTS = {
    "REWE SAGT DANKE": (5, 60),
    "LIDL DIENSTL. SAGT DANKE": (4, 45),
    "ALDI SUED": (4, 40),
    "DB VERTRIEB GMBH": (9, 60),
    "AMAZON EU S.A R.L.": (8, 80),
    "PAYPAL EUROPE": (5, 50),
    "MENSA TU DARMSTADT": (2.5, 7),
}


def german_amount(x: float) -> str:
    """1234.5 -> '1.234,50'"""
    s = f"{x:,.2f}"  # 1,234.50
    return s.replace(",", "X").replace(".", ",").replace("X", ".")


def main() -> None:
    random.seed(42)
    rows = []
    d = START
    while d <= END:
        if d.day == 1:
            rows.append((d, "MIETE STUDIERENDENWERK DARMSTADT", -350.00))
            rows.append((d, "GEHALT WERKSTUDENT", 900.00))
        if d.day == 5:
            rows.append((d, "SPOTIFY AB", -10.99))
        for _ in range(random.randint(0, 3)):
            merchant = random.choice(list(MERCHANTS))
            lo, hi = MERCHANTS[merchant]
            rows.append((d, merchant, -round(random.uniform(lo, hi), 2)))
        d += timedelta(days=1)

    OUT.parent.mkdir(parents=True, exist_ok=True)
    with open(OUT, "w", encoding="latin-1", newline="") as f:
        w = csv.writer(f, delimiter=";")
        w.writerow(["Buchungstag", "Verwendungszweck", "Betrag"])
        for d, desc, amount in rows:
            w.writerow([d.strftime("%d.%m.%Y"), desc, german_amount(amount)])
    print(f"Wrote {len(rows)} transactions to {OUT}")


if __name__ == "__main__":
    main()
