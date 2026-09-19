"""Synthetic source-data generator.

Produces realistic *raw* marketplace data for the catalog: multi-channel
orders, order lines, product master rows, and daily inventory snapshots --
with the kind of dirtiness real marketplace exports actually contain
(nulls, duplicates, negative quantities, stringified prices, whitespace).

The Spark cleaning step and the data-quality suites exist to handle exactly
this. Deterministic given RANDOM_SEED.
"""
from __future__ import annotations

import datetime as dt

import numpy as np
import pandas as pd
from config.settings import SETTINGS

from ecl.catalog import build_catalog

_US_STATES = [
    "IL", "TX", "CA", "FL", "OH", "PA", "KY", "CO", "OK", "NY",
    "GA", "NC", "TN", "AZ", "WA", "MO", "MI", "IN", "WI", "VA",
]

# Month -> demand multiplier. Equestrian gear peaks spring & fall.
_SEASONALITY = {
    1: 0.80, 2: 0.85, 3: 1.10, 4: 1.25, 5: 1.20, 6: 1.05,
    7: 0.95, 8: 1.00, 9: 1.20, 10: 1.15, 11: 1.05, 12: 1.30,
}

_CHANNEL_WEIGHT = {"amazon": 0.42, "walmart": 0.18, "ebay": 0.16, "etsy": 0.12, "faire": 0.12}
# Realized selling price relative to MSRP on each channel.
_CHANNEL_PRICE_FACTOR = {"amazon": 1.00, "walmart": 0.97, "ebay": 0.95, "etsy": 1.02, "faire": 0.60}


def _daily_lambda(rng: np.random.Generator, n_products: int) -> np.ndarray:
    """A heavy-tailed base demand per SKU: a few heroes, a long tail."""
    return rng.lognormal(mean=-0.6, sigma=0.9, size=n_products)


def generate(seed: int | None = None) -> dict[str, pd.DataFrame]:
    """Generate the raw source tables. Returns {name: DataFrame}."""
    s = SETTINGS
    seed = s.random_seed if seed is None else seed
    rng = np.random.default_rng(seed)

    products = build_catalog()
    prod_df = pd.DataFrame(
        [
            {
                "sku": p.sku,
                "category": p.category,
                "product_line": p.product_line,
                "title": p.title,
                "color": p.color,
                "size": p.size,
                "msrp": p.msrp,
                "unit_cost": p.unit_cost,
            }
            for p in products
        ]
    )
    n = len(prod_df)
    base_lambda = _daily_lambda(rng, n)

    end = dt.date.today()
    start = end - dt.timedelta(days=s.history_days)
    dates = [start + dt.timedelta(days=i) for i in range((end - start).days)]

    channels = list(_CHANNEL_WEIGHT)
    ch_weights = np.array([_CHANNEL_WEIGHT[c] for c in channels])

    order_rows: list[dict] = []
    item_rows: list[dict] = []
    order_counter = 0

    msrp_arr = prod_df["msrp"].to_numpy()
    sku_arr = prod_df["sku"].to_numpy()

    for day in dates:
        season = _SEASONALITY[day.month]
        # Expected orders across all channels this day.
        day_lambda = base_lambda.sum() * season * 2.4
        n_orders = rng.poisson(day_lambda)
        if n_orders <= 0:
            continue
        day_channels = rng.choice(channels, size=n_orders, p=ch_weights / ch_weights.sum())
        # SKU purchase probability weighted by popularity * seasonality.
        sku_p = (base_lambda * season)
        sku_p = sku_p / sku_p.sum()

        for k in range(n_orders):
            order_counter += 1
            channel = str(day_channels[k])
            order_id = f"{channel[:2].upper()}-{day:%Y%m%d}-{order_counter:06d}"
            ts = dt.datetime.combine(day, dt.time(0)) + dt.timedelta(
                seconds=int(rng.integers(0, 86400))
            )
            n_lines = int(rng.integers(1, 4))
            picks = rng.choice(n, size=n_lines, replace=False, p=sku_p)
            state = _US_STATES[int(rng.integers(0, len(_US_STATES)))]
            order_rows.append(
                {
                    "order_id": order_id,
                    "order_ts": ts,
                    "channel": channel,
                    "customer_state": state,
                    "ship_country": "US",
                }
            )
            price_factor = _CHANNEL_PRICE_FACTOR[channel]
            for idx in picks:
                qty = int(rng.integers(1, 4))
                noise = 1.0 + rng.normal(0, 0.02)
                promo = rng.random() < 0.12
                disc = round(rng.uniform(0.05, 0.25), 2) if promo else 0.0
                unit_price = round(msrp_arr[idx] * price_factor * noise * (1 - disc), 2)
                item_rows.append(
                    {
                        "order_id": order_id,
                        "sku": str(sku_arr[idx]),
                        "quantity": qty,
                        "unit_price": unit_price,
                        "discount_pct": disc,
                    }
                )

    orders = pd.DataFrame(order_rows)
    items = pd.DataFrame(item_rows)

    inventory = _generate_inventory(rng, prod_df, items, dates)

    # Inject realistic raw-data defects that the pipeline must handle.
    orders, items = _inject_defects(rng, orders, items)

    return {
        "products": prod_df,
        "orders": orders,
        "order_items": items,
        "inventory_snapshots": inventory,
    }


def _generate_inventory(rng, prod_df, items, dates) -> pd.DataFrame:
    """Daily on-hand snapshot per SKU with simple reorder-point logic."""
    # Average daily units sold per sku (for setting stock levels).
    sold = items.groupby("sku")["quantity"].sum() if not items.empty else pd.Series(dtype=float)
    horizon = max(len(dates), 1)
    rows: list[dict] = []
    for sku in prod_df["sku"]:
        avg_daily = float(sold.get(sku, 0.0)) / horizon
        reorder_point = max(5, int(avg_daily * SETTINGS.reorder_lead_time_days))
        order_up_to = max(reorder_point * 3, 20)
        on_hand = order_up_to
        for day in dates:
            demand = rng.poisson(max(avg_daily, 0.02))
            on_hand = max(0, on_hand - int(demand))
            if on_hand <= reorder_point and rng.random() < 0.5:
                on_hand = order_up_to  # replenishment arrives
            rows.append(
                {
                    "snapshot_date": day,
                    "sku": sku,
                    "on_hand_units": on_hand,
                    "reorder_point": reorder_point,
                }
            )
    return pd.DataFrame(rows)


def _inject_defects(rng, orders: pd.DataFrame, items: pd.DataFrame):
    """Introduce ~1-2% dirty rows mirroring real marketplace export quirks."""
    if orders.empty or items.empty:
        return orders, items

    orders = orders.copy()
    items = items.copy()

    # 1) Null out some customer_state values.
    mask = rng.random(len(orders)) < 0.015
    orders.loc[mask, "customer_state"] = None

    # 2) Whitespace pollution on some SKUs (leading/trailing spaces).
    imask = rng.random(len(items)) < 0.02
    items.loc[imask, "sku"] = " " + items.loc[imask, "sku"].astype(str) + " "

    # 3) A handful of negative / zero quantities (returns keyed wrong).
    nmask = rng.random(len(items)) < 0.006
    items.loc[nmask, "quantity"] = rng.integers(-2, 1, size=int(nmask.sum()))

    # 4) Duplicate ~0.5% of order-item rows (double-exported lines).
    dup = items.sample(frac=0.005, random_state=1)
    items = pd.concat([items, dup], ignore_index=True)

    # 5) unit_price as an occasional string (schema drift on export).
    smask = rng.random(len(items)) < 0.004
    items["unit_price"] = items["unit_price"].astype(object)
    items.loc[smask, "unit_price"] = items.loc[smask, "unit_price"].apply(lambda v: f"${v}")

    return orders, items
