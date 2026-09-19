"""Canonical product catalog for Majestic Ally.

Models the real shape of the business: ~140 SKUs across 13 equestrian & dog
categories. SKUs are generated deterministically so the whole project is
reproducible (same seed -> same catalog -> same data -> same test assertions).

This is the single source of truth the rest of the pipeline conforms to.
"""
from __future__ import annotations

import hashlib
from dataclasses import dataclass

# (category, product_line, base_msrp, count_of_skus, cost_ratio)
# cost_ratio = landed unit cost as a fraction of MSRP (gross margin = 1 - ratio).
_CATEGORY_SPEC: list[tuple[str, str, float, int, float]] = [
    ("Slow-Feed Hay Feeders", "HayFeeder", 79.99, 10, 0.42),
    ("Halters", "Halter", 34.99, 14, 0.38),
    ("Headstalls", "Headstall", 64.99, 12, 0.45),
    ("Breast Collars", "BreastCollar", 74.99, 11, 0.46),
    ("Bridles", "Bridle", 89.99, 12, 0.47),
    ("Reins", "Reins", 39.99, 10, 0.40),
    ("Horse Blankets", "Blanket", 119.99, 13, 0.44),
    ("Boots & Wraps", "Boots", 49.99, 12, 0.39),
    ("Saddle Accessories", "SaddleAcc", 44.99, 11, 0.41),
    ("Fly Masks", "FlyMask", 29.99, 9, 0.37),
    ("Girths & Cinches", "Girth", 54.99, 10, 0.43),
    ("Halter Fleece Sets", "FleeceSet", 24.99, 8, 0.36),
    ("Dog Collars & Leashes", "DogCollar", 27.99, 11, 0.35),
]

_COLORS = ["Black", "Brown", "Havana", "Burgundy", "Navy", "Teal", "Hunter", "Tan"]
_SIZES = ["Pony", "Cob", "Horse", "Full", "Oversize", "S", "M", "L", "XL"]


@dataclass(frozen=True)
class Product:
    sku: str
    category: str
    product_line: str
    title: str
    color: str
    size: str
    msrp: float
    unit_cost: float

    @property
    def gross_margin(self) -> float:
        return round(1.0 - (self.unit_cost / self.msrp), 4)


def _stable_int(*parts: str) -> int:
    """Deterministic pseudo-random int from string parts (seed-free, stable)."""
    h = hashlib.sha256("|".join(parts).encode()).hexdigest()
    return int(h[:8], 16)


def build_catalog() -> list[Product]:
    """Return the full deterministic catalog (~140 SKUs)."""
    products: list[Product] = []
    for cat, line, base_msrp, n, cost_ratio in _CATEGORY_SPEC:
        for i in range(1, n + 1):
            sku = f"MA-{line[:3].upper()}-{i:03d}"
            seed = _stable_int(sku)
            color = _COLORS[seed % len(_COLORS)]
            size = _SIZES[(seed // 7) % len(_SIZES)]
            # Spread MSRP +/-25% around the line's base price, in tidy .99 steps.
            spread = 0.75 + ((seed % 50) / 100.0)  # 0.75 .. 1.24
            msrp = round(base_msrp * spread) - 0.01
            unit_cost = round(msrp * cost_ratio, 2)
            title = f"Majestic Ally {color} {size} {cat[:-1] if cat.endswith('s') else cat}"
            products.append(
                Product(
                    sku=sku,
                    category=cat,
                    product_line=line,
                    title=title,
                    color=color,
                    size=size,
                    msrp=msrp,
                    unit_cost=unit_cost,
                )
            )
    return products


def catalog_size() -> int:
    return sum(spec[3] for spec in _CATEGORY_SPEC)


CATEGORIES = [spec[0] for spec in _CATEGORY_SPEC]
