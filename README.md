# bank-analyzer

Import German bank statement CSVs, categorize transactions with keyword rules, store them in SQLite (`data/bank.db`) and explore them in an online-banking style web app (FastAPI + HTML/CSS/JS) or the Streamlit dashboard.

## Setup (Windows)

```powershell
py -3.13 -m venv .venv
.venv\Scripts\Activate.ps1
pip install -r requirements.txt
```

(macOS/Linux: `python3 -m venv .venv && source .venv/bin/activate`)

## Quick start with fake data

```powershell
python scripts/generate_fake_data.py   # writes data/fake_statement.csv (6 months)
python main.py                         # import, categorize, print summary
uvicorn server:app --reload            # web app: http://localhost:8000
streamlit run dashboard.py             # alternative dashboard: http://localhost:8501
```

## Web app

`server.py` serves a JSON API and the frontend in `web/` (plain HTML/CSS/JS, no build step; charts with Chart.js from a CDN).

- **Overview**: account balance, income/spending/net/savings rate for the chosen period (1M, 3M, 6M, 12M, All), income vs. spending per month, spending by category (click a category to see its transactions), recent transactions.
- **Transactions**: grouped by day, search, income/expense filter, category chips, CSV export of the current selection.
- **Analysis**: spending per month by category, one category over time, top merchants.
- **Import CSV** (top right): upload a statement from the browser; it is categorized and stored like `main.py` does.

API: `GET /api/transactions`, `GET /api/categories`, `POST /api/import` (multipart field `file`).

Re-running `main.py` on the same file adds no duplicates (rows are unique on date + description + amount).

## Using your real bank statement

1. In your online banking, open the account's transaction list and export it as **CSV** (often "Umsätze exportieren" → "CSV" or "CSV-CAMT").
2. Save it in `data/` (this folder is gitignored, so real data is never committed).
3. Check the header row. The loader expects `;` as the separator, Latin-1 encoding, `1.234,56` amounts and `dd.mm.yyyy` dates, with the columns `Buchungstag`, `Verwendungszweck` and `Betrag`. If your bank uses other names (e.g. `Buchungsdatum`, `Buchungstext`, `Betrag (€)`), edit `COLUMN_MAP` in `analyzer/loader.py`. Some banks add a few info lines above the header; delete them or pass `skiprows=` to `pd.read_csv`.
4. Import it:

   ```powershell
   python main.py data/my_statement.csv
   ```

5. Look at the `Other` rows printed at the end and add keywords to `categories.json` (first matching category wins). To recategorize existing rows, delete `data/bank.db` and import again.

The dashboard caches the data. After importing, use the "⋮" menu → **Clear cache**, or restart it.

## Project layout

| Path | Purpose |
| --- | --- |
| `analyzer/loader.py` | read and clean bank CSVs |
| `analyzer/categorizer.py` | keyword rules → category |
| `analyzer/db.py` | SQLite schema, inserts, queries |
| `analyzer/report.py` | monthly summary + matplotlib chart |
| `categories.json` | keyword rules |
| `main.py` | CSV → categorize → database → summary |
| `dashboard.py` | Streamlit dashboard |
| `server.py` | FastAPI: JSON API + serves `web/` |
| `web/` | banking-style frontend (`index.html`, `styles.css`, `app.js`) |
