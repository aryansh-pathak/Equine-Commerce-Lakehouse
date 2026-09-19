with src as (
    select * from {{ source('raw', 'orders') }}
)
select
    order_id,
    cast(order_ts as timestamp)  as order_ts,
    cast(order_ts as date)       as order_date,
    lower(trim(channel))         as channel,
    customer_state,
    ship_country
from src
