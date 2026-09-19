with src as (
    select * from {{ source('raw', 'products') }}
)
select
    trim(sku)                                    as sku,
    category,
    product_line,
    title,
    color,
    size,
    cast(msrp as double)                         as msrp,
    cast(unit_cost as double)                    as unit_cost,
    round(1 - cast(unit_cost as double) / nullif(cast(msrp as double), 0), 4) as gross_margin
from src
