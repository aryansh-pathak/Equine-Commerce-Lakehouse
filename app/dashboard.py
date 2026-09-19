"""Streamlit analytics app for the commerce lakehouse.

Reads the modeled warehouse (DuckDB) and serves the decision views the marts
were built for: channel economics, SKU velocity, and stockout risk.

Run:  streamlit run app/dashboard.py
"""
from __future__ import annotations

import sys
from pathlib import Path

import duckdb
import pandas as pd
import plotly.express as px
import streamlit as st

REPO_ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(REPO_ROOT))
from config.settings import SETTINGS  # noqa: E402

st.set_page_config(page_title="Equine Commerce Lakehouse", layout="wide")

PALETTE = ["#2f5233", "#5a8f5e", "#b8860b", "#7c4a2d", "#4a6fa5"]


@st.cache_data(ttl=300)
def q(sql: str) -> pd.DataFrame:
    con = duckdb.connect(SETTINGS.duckdb_path, read_only=True)
    try:
        return con.execute(sql).fetch_df()
    finally:
        con.close()


st.title("🐎 Majestic Ally — Commerce Lakehouse")
st.caption("Multi-marketplace ELT → dimensional warehouse → analytics. "
           "Data quality gated; refreshed by the pipeline.")

try:
    kpis = q("""
        select
            (select count(*) from main.dim_product)                as skus,
            (select count(distinct order_id) from main.fct_orders)  as orders,
            (select round(sum(line_gross),0) from main.fct_orders)  as gross_rev,
            (select round(sum(line_net_margin),0) from main.fct_orders) as net_margin,
            (select count(*) from main.mart_sku_velocity where stockout_risk='reorder_now') as reorder_now
    """).iloc[0]
except Exception:  # noqa: BLE001
    st.error("Warehouse not found. Run `make pipeline` first to build it.")
    st.stop()

c1, c2, c3, c4, c5 = st.columns(5)
c1.metric("SKUs", f"{int(kpis.skus)}")
c2.metric("Orders", f"{int(kpis.orders):,}")
c3.metric("Gross revenue", f"${kpis.gross_rev:,.0f}")
c4.metric("Net margin", f"${kpis.net_margin:,.0f}")
c5.metric("Reorder now", f"{int(kpis.reorder_now)}", help="SKUs with days-of-cover below lead time")

st.divider()

left, right = st.columns(2)
with left:
    st.subheader("Channel economics")
    chan = q("select * from main.mart_channel_performance")
    fig = px.bar(chan, x="channel", y=["gross_revenue", "net_margin"],
                 barmode="group", color_discrete_sequence=PALETTE)
    fig.update_layout(legend_title_text="", height=360, margin=dict(t=10))
    st.plotly_chart(fig, width="stretch")
    st.dataframe(chan, width="stretch", hide_index=True)

with right:
    st.subheader("Revenue by category")
    cat = q("""
        select p.category, round(sum(f.line_gross),0) as revenue
        from main.fct_orders f join main.dim_product p on f.sku=p.sku
        group by 1 order by revenue desc
    """)
    fig2 = px.bar(cat, x="revenue", y="category", orientation="h",
                  color_discrete_sequence=PALETTE)
    fig2.update_layout(height=360, margin=dict(t=10), yaxis=dict(autorange="reversed"))
    st.plotly_chart(fig2, width="stretch")

st.divider()
st.subheader("SKU velocity & stockout risk")
risk_filter = st.multiselect(
    "Filter by stockout risk",
    options=["reorder_now", "watch", "healthy", "no_recent_sales"],
    default=["reorder_now", "watch"],
)
vel = q("select * from main.mart_sku_velocity order by units_28d desc")
if risk_filter:
    vel = vel[vel["stockout_risk"].isin(risk_filter)]
st.dataframe(
    vel[["sku", "category", "title", "units_7d", "units_28d",
         "avg_daily_velocity_28d", "on_hand_units", "days_of_cover", "stockout_risk"]],
    width="stretch", hide_index=True, height=420,
)

st.caption("Built with DuckDB + dbt + PySpark. Swap the warehouse to "
           "Snowflake/BigQuery via config — models unchanged.")
