-- Date spine covering the observed order history.
with bounds as (
    select min(order_date) as d0, max(order_date) as d1
    from {{ ref('stg_orders') }}
),
spine as (
    select cast(gs as date) as date_day
    from bounds,
         generate_series(bounds.d0, bounds.d1, interval '1 day') as g(gs)
)
select
    date_day,
    extract(year  from date_day)  as year,
    extract(month from date_day)  as month,
    extract(day   from date_day)  as day,
    extract(dow   from date_day)  as day_of_week,
    strftime(date_day, '%Y-%m')   as year_month
from spine
