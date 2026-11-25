"""Web app: JSON API + online-banking style frontend (web/).

Run: uvicorn server:app --reload   ->  http://localhost:8000
"""
import io
from pathlib import Path

from fastapi import FastAPI, File, HTTPException, UploadFile
from fastapi.staticfiles import StaticFiles

from analyzer.categorizer import CATEGORY_COLORS, DEFAULT_RULES_PATH, categorize, load_rules
from analyzer.db import DB_PATH, init_db, insert_transactions, load_all
from analyzer.loader import load_statement

WEB_DIR = Path(__file__).resolve().parent / "web"
MAX_UPLOAD_BYTES = 5 * 1024 * 1024


def create_app(db_path: str | Path = DB_PATH, rules_path: str | Path = DEFAULT_RULES_PATH) -> FastAPI:
    app = FastAPI(title="Bank Analyzer")

    @app.get("/api/transactions")
    def transactions() -> list[dict]:
        init_db(db_path)
        df = load_all(db_path)
        return [
            {
                "id": int(r.id),
                "date": r.date.strftime("%Y-%m-%d"),
                "description": str(r.description),
                "amount": float(r.amount),
                "category": str(r.category),
            }
            for r in df.itertuples(index=False)
        ]

    @app.get("/api/categories")
    def categories() -> list[dict]:
        names = list(load_rules(rules_path))
        if "Other" not in names:
            names.append("Other")
        return [{"name": n, "color": CATEGORY_COLORS.get(n, "#999999")} for n in names]

    @app.post("/api/import")
    async def import_statement(file: UploadFile = File(...)) -> dict:
        content = await file.read(MAX_UPLOAD_BYTES + 1)
        if len(content) > MAX_UPLOAD_BYTES:
            raise HTTPException(413, "File too large (max 5 MB).")
        try:
            df = load_statement(io.BytesIO(content))
        except ValueError as e:  # also covers parser, date and encoding errors
            raise HTTPException(400, f"Could not read this CSV: {e}") from e

        rules = load_rules(rules_path)
        df["category"] = df["description"].apply(lambda d: categorize(d, rules))
        init_db(db_path)
        new_rows = insert_transactions(df, db_path)
        return {"filename": file.filename, "rows": len(df), "new": new_rows}

    # Frontend last, so /api/* routes take precedence.
    app.mount("/", StaticFiles(directory=WEB_DIR, html=True), name="web")
    return app


app = create_app()
