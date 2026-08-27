-- Q2: evolução de um insumo/medida ao longo do tempo, por UF/regime.
-- valor_anterior/variacao_percentual são nulos no primeiro período
-- observado de uma série — não há com o que comparar ainda.
with ordenado as (
    select
        *,
        lag(valor) over (
            partition by insumo_id, state_slug, desonerado, medida
            order by period_start
        ) as valor_anterior,
        lag(period_start) over (
            partition by insumo_id, state_slug, desonerado, medida
            order by period_start
        ) as period_start_anterior
    from {{ ref('fato_medicao') }}
)

select
    dim_insumo.tipo,
    dim_insumo.codigo,
    dim_insumo.descricao,
    ordenado.medida,
    dim_uf.state_slug,
    dim_uf.state_name,
    ordenado.desonerado,
    ordenado.period_start,
    ordenado.valor,
    ordenado.period_start_anterior,
    ordenado.valor_anterior,
    ordenado.valor - ordenado.valor_anterior as variacao_absoluta,
    case
        when ordenado.valor_anterior is null or ordenado.valor_anterior = 0 then null
        else (ordenado.valor - ordenado.valor_anterior) / ordenado.valor_anterior
    end as variacao_percentual
from ordenado
inner join {{ ref('dim_insumo') }} as dim_insumo on ordenado.insumo_id = dim_insumo.insumo_id
inner join {{ ref('dim_uf') }} as dim_uf on ordenado.state_slug = dim_uf.state_slug
