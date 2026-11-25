"""Streamlit dashboard. Run: streamlit run dashboard.py"""
import pandas as pd
import plotly.express as px
import streamlit as st

from analyzer.categorizer import CATEGORY_COLORS as BASE_COLORS, load_rules
from analyzer.db import init_db, load_all

st.set_page_config(page_title="Bank Analyzer", page_icon="💶", layout="wide")

CATEGORY_COLORS = dict(BASE_COLORS)  # copy: user categories are added below
CATEGORY_ORDER = list(CATEGORY_COLORS)


def euro(x: float) -> str:
    return f"{x:,.2f} €".replace(",", "X").replace(".", ",").replace("X", ".")


@st.cache_data
def get_data() -> pd.DataFrame:
    init_db()
    return load_all()


df = get_data()
st.title("💶 Bank Analyzer")

if df.empty:
    st.warning("No transactions yet. Run `python main.py` first to import a statement.")
    st.stop()

# Categories from rules that aren't in the fixed map (user-added) get grey fallback.
for cat in load_rules():
    CATEGORY_COLORS.setdefault(cat, "#999999")

# ---------- Sidebar filters ----------
st.sidebar.header("Filters")
min_d, max_d = df["date"].min().date(), df["date"].max().date()
date_range = st.sidebar.date_input(
    "Date range", value=(min_d, max_d), min_value=min_d, max_value=max_d
)
all_cats = [c for c in CATEGORY_ORDER if c in set(df["category"])] + sorted(
    set(df["category"]) - set(CATEGORY_ORDER)
)
selected_cats = st.sidebar.multiselect("Categories", all_cats, default=all_cats)

if not isinstance(date_range, (tuple, list)) or len(date_range) != 2:
    st.info("Select an end date to complete the date range.")
    st.stop()

start, end = pd.Timestamp(date_range[0]), pd.Timestamp(date_range[1])
f = df[df["date"].between(start, end) & df["category"].isin(selected_cats)]

if f.empty:
    st.info("No transactions match the current filters.")
    st.stop()

# ---------- Stat tiles ----------
income = f.loc[f["amount"] > 0, "amount"].sum()
spent = -f.loc[f["amount"] < 0, "amount"].sum()
n_months = max(f["date"].dt.to_period("M").nunique(), 1)

c1, c2, c3, c4 = st.columns(4)
c1.metric("Income", euro(income))
c2.metric("Spent", euro(spent))
c3.metric("Net", euro(income - spent))
c4.metric("Avg spent / month", euro(spent / n_months))

# ---------- Stacked bar: spending per month by category ----------
spend = f[(f["amount"] < 0) & (f["category"] != "Income")].copy()
spend["month"] = spend["date"].dt.strftime("%Y-%m")
spend["spent"] = -spend["amount"]
monthly = spend.groupby(["month", "category"], as_index=False)["spent"].sum()

st.subheader("Spending per month by category")
if monthly.empty:
    st.info("No spending in the current selection.")
else:
    fig = px.bar(
        monthly,
        x="month",
        y="spent",
        color="category",
        color_discrete_map=CATEGORY_COLORS,
        category_orders={"category": [c for c in all_cats if c != "Income"]},
        labels={"month": "", "spent": "€", "category": "Category"},
    )
    fig.update_traces(
        marker_line_color="white",
        marker_line_width=2,
        hovertemplate="%{x}<br>%{fullData.name}: %{y:,.2f} €<extra></extra>",
    )
    fig.update_layout(barmode="stack", bargap=0.35, legend_title_text="")
    st.plotly_chart(fig, width="stretch")

# ---------- Line: one category over time ----------
st.subheader("Category over time")
line_cats = [c for c in all_cats if c in set(f["category"])]
cat = st.selectbox("Category", line_cats)
cat_df = f[f["category"] == cat].copy()
cat_df["month"] = cat_df["date"].dt.to_period("M").dt.to_timestamp()
cat_monthly = (
    cat_df.groupby("month", as_index=False)["amount"].sum().assign(value=lambda d: d["amount"].abs())
)
fig2 = px.line(
    cat_monthly,
    x="month",
    y="value",
    markers=True,
    labels={"month": "", "value": "€"},
    color_discrete_sequence=[CATEGORY_COLORS.get(cat, "#999999")],
)
fig2.update_traces(
    line_width=2,
    marker_size=8,
    name=cat,
    hovertemplate="%{y:,.2f} €",
)
fig2.update_layout(hovermode="x unified", xaxis_tickformat="%b %Y")
st.plotly_chart(fig2, width="stretch")

# ---------- Table ----------
st.subheader("Transactions")
table = f.sort_values(["date", "id"], ascending=False)[["date", "description", "category", "amount"]]
st.dataframe(
    table,
    width="stretch",
    hide_index=True,
    column_config={
        "date": st.column_config.DateColumn("Date", format="DD.MM.YYYY"),
        "description": "Description",
        "category": "Category",
        "amount": st.column_config.NumberColumn("Amount (€)", format="%.2f"),
    },
)
