select
    sku,
    category,
    product_line,
    title,
    color,
    size,
    msrp,
    unit_cost,
    gross_margin
from {{ ref('stg_products') }}
