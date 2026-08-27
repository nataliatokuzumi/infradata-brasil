-- Q4: comparação de um insumo entre UFs, num período — fato_medicao com
-- nomes legíveis já joinados. Não filtra nem agrega nada; o consumidor
-- filtra por tipo/codigo/período e compara as linhas por state_name.
select
    dim_insumo.tipo,
    dim_insumo.codigo,
    dim_insumo.descricao,
    fato_medicao.medida,
    fato_medicao.desonerado,
    dim_uf.state_slug,
    dim_uf.state_code,
    dim_uf.state_name,
    dim_uf.region,
    fato_medicao.period_start,
    fato_medicao.valor
from {{ ref('fato_medicao') }} as fato_medicao
inner join {{ ref('dim_insumo') }} as dim_insumo on fato_medicao.insumo_id = dim_insumo.insumo_id
inner join {{ ref('dim_uf') }} as dim_uf on fato_medicao.state_slug = dim_uf.state_slug
