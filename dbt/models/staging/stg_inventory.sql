with src as (
    select * from {{ source('raw', 'inventory_snapshots') }}
)
select
    cast(snapshot_date as date)     as snapshot_date,
    trim(sku)                       as sku,
    cast(on_hand_units as integer)  as on_hand_units,
    cast(reorder_point as integer)  as reorder_point
from src
