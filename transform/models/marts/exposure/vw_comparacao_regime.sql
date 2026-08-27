-- Q3: desonerado vs. não desonerado lado a lado. materiais não aparece
-- aqui — SICRO não publica variante desonerado pra preço de material.
with regime_desonerado as (
    select insumo_id, state_slug, period_start, medida, valor as valor_desonerado
    from {{ ref('fato_medicao') }}
    where desonerado
),

regime_nao_desonerado as (
    select insumo_id, state_slug, period_start, medida, valor as valor_nao_desonerado
    from {{ ref('fato_medicao') }}
    where not desonerado
)

select
    dim_insumo.tipo,
    dim_insumo.codigo,
    dim_insumo.descricao,
    regime_desonerado.medida,
    dim_uf.state_slug,
    dim_uf.state_name,
    regime_desonerado.period_start,
    regime_desonerado.valor_desonerado,
    regime_nao_desonerado.valor_nao_desonerado,
    regime_desonerado.valor_desonerado - regime_nao_desonerado.valor_nao_desonerado as diferenca_absoluta,
    case
        when regime_nao_desonerado.valor_nao_desonerado is null or regime_nao_desonerado.valor_nao_desonerado = 0 then null
        else (regime_desonerado.valor_desonerado - regime_nao_desonerado.valor_nao_desonerado) / regime_nao_desonerado.valor_nao_desonerado
    end as diferenca_percentual
from regime_desonerado
inner join regime_nao_desonerado
    on  regime_desonerado.insumo_id    = regime_nao_desonerado.insumo_id
    and regime_desonerado.state_slug   = regime_nao_desonerado.state_slug
    and regime_desonerado.period_start = regime_nao_desonerado.period_start
    and regime_desonerado.medida       = regime_nao_desonerado.medida
inner join {{ ref('dim_insumo') }} as dim_insumo on regime_desonerado.insumo_id = dim_insumo.insumo_id
inner join {{ ref('dim_uf') }} as dim_uf on regime_desonerado.state_slug = dim_uf.state_slug
