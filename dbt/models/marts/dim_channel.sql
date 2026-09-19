-- Sales channels and their marketplace fee (referral commission) rates.
with channels as (
    select * from (
        values
            ('amazon',  0.150),
            ('walmart', 0.120),
            ('ebay',    0.130),
            ('etsy',    0.065),
            ('faire',   0.150)
    ) as t(channel, fee_rate)
)
select
    channel,
    fee_rate,
    case when channel = 'faire' then 'wholesale' else 'retail' end as channel_type
from channels
