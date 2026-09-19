-- The headline mart: SKU sales velocity + stockout risk.
-- Answers "what is selling, how fast, and what am I about to run out of?" --
-- the exact input for assortment and reorder decisions.
with as_of as (
    select max(order_date) as as_of_date from {{ ref('fct_orders') }}
),
sales as (
    select
        f.sku,
        sum(case when f.order_date > (select as_of_date from as_of) - interval '7 day'
                 then f.quantity else 0 end)  as units_7d,
        sum(case when f.order_date > (select as_of_date from as_of) - interval '28 day'
                 then f.quantity else 0 end)  as units_28d,
        sum(f.quantity)                       as units_lifetime,
        round(sum(f.line_net_margin), 2)      as net_margin_lifetime
    from {{ ref('fct_orders') }} f
    group by f.sku
),
latest_inv as (
    select
        sku, on_hand_units, reorder_point,
        row_number() over (partition by sku order by snapshot_date desc) as rn
    from {{ ref('fct_inventory_snapshot') }}
),
inv as (
    select sku, on_hand_units, reorder_point from latest_inv where rn = 1
),
joined as (
    select
        p.sku,
        p.category,
        p.title,
        p.msrp,
        coalesce(s.units_7d, 0)                          as units_7d,
        coalesce(s.units_28d, 0)                         as units_28d,
        coalesce(s.units_lifetime, 0)                    as units_lifetime,
        coalesce(s.net_margin_lifetime, 0)               as net_margin_lifetime,
        round(coalesce(s.units_28d, 0) / 28.0, 3)        as avg_daily_velocity_28d,
        i.on_hand_units,
        i.reorder_point
    from {{ ref('dim_product') }} p
    left join sales s on p.sku = s.sku
    left join inv   i on p.sku = i.sku
)
select
    *,
    case when units_28d = 0 then null
         else round(on_hand_units / (units_28d / 28.0), 1) end as days_of_cover,
    case
        when units_28d = 0 then 'no_recent_sales'
        when on_hand_units / nullif(units_28d / 28.0, 0) < {{ var('lead_time_days') }}
            then 'reorder_now'
        when on_hand_units / nullif(units_28d / 28.0, 0) < {{ var('lead_time_days') }} * 2
            then 'watch'
        else 'healthy'
    end as stockout_risk
from joined
