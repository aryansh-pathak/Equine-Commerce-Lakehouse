-- Grain: one row per order line. Enriched with product cost and channel fee
-- so revenue, COGS, marketplace fees, and net margin are all additive.
with items as (
    select * from {{ ref('stg_order_items') }}
),
orders as (
    select * from {{ ref('stg_orders') }}
),
product as (
    select * from {{ ref('dim_product') }}
),
channel as (
    select * from {{ ref('dim_channel') }}
)
select
    md5(
        i.order_id || '|' || i.sku || '|' ||
        cast(i.quantity as varchar) || '|' || cast(i.unit_price as varchar)
    )                                                   as order_line_key,
    i.order_id,
    o.order_date,
    o.order_ts,
    o.channel,
    o.customer_state,
    i.sku,
    p.category,
    i.quantity,
    i.unit_price,
    i.discount_pct,
    i.line_gross,
    round(i.line_gross * c.fee_rate, 2)                 as channel_fee,
    round(p.unit_cost * i.quantity, 2)                  as line_cost,
    round(
        i.line_gross - (i.line_gross * c.fee_rate) - (p.unit_cost * i.quantity), 2
    )                                                   as line_net_margin
from items i
join orders  o on i.order_id = o.order_id
join product p on i.sku      = p.sku
join channel c on o.channel  = c.channel
