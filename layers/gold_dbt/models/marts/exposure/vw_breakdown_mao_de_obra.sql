-- Q8: breakdown of mao_de_obra cost (salário, encargos, periculosidade) —
-- explains why labor cost varies between UFs, not just that it varies.
-- salario/encargos_totais/periculosidade_insalubridade are null when
-- schema_version = '2025_plus' (see stg_sicro__mao_de_obra.sql) — absence
-- of data, not zero.
select
    dim_insumo.codigo,
    dim_insumo.descricao,
    dim_insumo.unidade,
    dim_uf.state_slug,
    dim_uf.state_name,
    dim_uf.region,
    fato_custo_mao_de_obra.period_start,
    fato_custo_mao_de_obra.desonerado,
    fato_custo_mao_de_obra.salario,
    fato_custo_mao_de_obra.encargos_totais,
    fato_custo_mao_de_obra.periculosidade_insalubridade,
    fato_custo_mao_de_obra.custo,
    fato_custo_mao_de_obra.schema_version
from {{ ref('fato_custo_mao_de_obra') }} as fato_custo_mao_de_obra
inner join {{ ref('dim_insumo') }} as dim_insumo on fato_custo_mao_de_obra.insumo_id = dim_insumo.insumo_id
inner join {{ ref('dim_uf') }} as dim_uf on fato_custo_mao_de_obra.state_slug = dim_uf.state_slug
