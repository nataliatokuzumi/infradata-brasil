-- Q5: cumulative reajuste index by category x UF x regime, over time.
-- Method: each series (insumo x UF x regime x medida) is expressed as a
-- ratio to its own first observed value (base); indice is the median of
-- those ratios *100 across all insumos in the group for that period —
-- base-100 at the start of each series, not a single fixed calendar, since
-- different series enter the dataset at different times.
-- n_insumos is the sample size behind the index for that period — treat
-- periods with low n_insumos with caution.
with base as (
    select
        insumo_id, state_slug, desonerado, medida,
        arg_min(valor, period_start) as valor_base
    from {{ ref('fato_medicao') }}
    group by 1, 2, 3, 4
),

relativo as (
    select
        fato_medicao.state_slug,
        fato_medicao.desonerado,
        fato_medicao.period_start,
        dim_insumo.tipo,
        fato_medicao.valor / base.valor_base as valor_relativo
    from {{ ref('fato_medicao') }} as fato_medicao
    inner join base
        on  fato_medicao.insumo_id  = base.insumo_id
        and fato_medicao.state_slug = base.state_slug
        and fato_medicao.desonerado = base.desonerado
        and fato_medicao.medida     = base.medida
    inner join {{ ref('dim_insumo') }} as dim_insumo on fato_medicao.insumo_id = dim_insumo.insumo_id
    where base.valor_base is not null and base.valor_base != 0
)

select
    tipo,
    state_slug,
    desonerado,
    period_start,
    median(valor_relativo) * 100 as indice,
    count(*) as n_insumos
from relativo
group by 1, 2, 3, 4
order by 1, 2, 3, 4
