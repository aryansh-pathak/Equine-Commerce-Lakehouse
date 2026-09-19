-- Grain: one row per (snapshot_date, sku). Daily on-hand position.
select
    s.snapshot_date,
    s.sku,
    p.category,
    s.on_hand_units,
    s.reorder_point,
    case when s.on_hand_units <= s.reorder_point then true else false end as below_reorder_point
from {{ ref('stg_inventory') }} s
join {{ ref('dim_product') }} p on s.sku = p.sku
