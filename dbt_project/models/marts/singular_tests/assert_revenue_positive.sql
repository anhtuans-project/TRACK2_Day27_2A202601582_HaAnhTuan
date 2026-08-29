select * from {{ ref('fct_daily_revenue') }} where daily_revenue < 0
