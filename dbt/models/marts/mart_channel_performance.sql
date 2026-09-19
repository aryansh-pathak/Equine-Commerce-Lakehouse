-- Channel economics: revenue, fees, COGS, and net margin by marketplace.
select
    channel,
    count(distinct order_id)                                        as orders,
    sum(quantity)                                                   as units,
    round(sum(line_gross), 2)                                       as gross_revenue,
    round(sum(channel_fee), 2)                                      as marketplace_fees,
    round(sum(line_cost), 2)                                        as cogs,
    round(sum(line_net_margin), 2)                                  as net_margin,
    round(100.0 * sum(line_net_margin) / nullif(sum(line_gross), 0), 1) as net_margin_pct
from {{ ref('fct_orders') }}
group by channel
order by net_margin desc
