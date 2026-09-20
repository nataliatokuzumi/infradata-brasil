-- Grain: 1 row per period (year, month) in which at least one SICRO report
-- was published. SICRO publishes quarterly (confirmed in the data: only
-- January/April/July/October appear), hence the trimestre column.
with periodos as (
    select distinct cast(year as integer) as ano, month as mes from {{ ref('stg_sicro__materiais') }}
    union
    select distinct cast(year as integer) as ano, month as mes from {{ ref('stg_sicro__equipamentos') }}
    union
    select distinct cast(year as integer) as ano, month as mes from {{ ref('stg_sicro__mao_de_obra') }}
)

select
    make_date(periodos.ano, seed_month.month_number, 1) as period_start,
    periodos.ano,
    periodos.mes,
    seed_month.month_number as mes_numero,
    ((seed_month.month_number - 1) / 3) + 1 as trimestre
from periodos
left join {{ ref('seed_month') }} as seed_month
    on periodos.mes = seed_month.month_name
