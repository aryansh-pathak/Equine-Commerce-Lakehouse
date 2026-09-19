with src as (
    select * from {{ source('raw', 'order_items') }}
)
select
    order_id,
    trim(sku)                             as sku,
    cast(quantity as integer)             as quantity,
    cast(unit_price as double)            as unit_price,
    coalesce(cast(discount_pct as double), 0) as discount_pct,
    cast(line_gross as double)            as line_gross
from src
