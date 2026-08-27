-- Q1: preço/custo mais recente por insumo x UF x regime x medida.
with ranqueado as (
    select
        fato_medicao.*,
        row_number() over (
            partition by insumo_id, state_slug, desonerado, medida
            order by period_start desc
        ) as posicao
    from {{ ref('fato_medicao') }} as fato_medicao
)

select
    dim_insumo.tipo,
    dim_insumo.codigo,
    dim_insumo.descricao,
    dim_insumo.unidade,
    ranqueado.medida,
    ranqueado.valor,
    ranqueado.desonerado,
    dim_uf.state_slug,
    dim_uf.state_code,
    dim_uf.state_name,
    dim_uf.region,
    ranqueado.period_start
from ranqueado
inner join {{ ref('dim_insumo') }} as dim_insumo on ranqueado.insumo_id = dim_insumo.insumo_id
inner join {{ ref('dim_uf') }} as dim_uf on ranqueado.state_slug = dim_uf.state_slug
where ranqueado.posicao = 1
