-- Q4: comparing one insumo across UFs, for a given period — fato_medicao
-- with readable names already joined in. Doesn't filter or aggregate
-- anything; the consumer filters by tipo/codigo/period and compares rows by
-- state_name.
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
