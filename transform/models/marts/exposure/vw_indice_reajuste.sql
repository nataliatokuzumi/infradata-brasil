-- Q5: índice de reajuste acumulado por categoria x UF x regime, ao longo do
-- tempo. Método: cada série (insumo x UF x regime x medida) é expressa como
-- razão pro seu próprio primeiro valor observado (base); indice é a mediana
-- dessas razões *100 entre todos os insumos do grupo naquele período —
-- base-100 no início de cada série, não um calendário fixo único, já que
-- séries diferentes entram no dataset em momentos diferentes.
-- n_insumos é o tamanho da amostra por trás do índice naquele período —
-- trate períodos com n_insumos baixo com cautela.
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
