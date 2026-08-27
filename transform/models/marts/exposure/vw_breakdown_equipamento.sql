-- Q7: decomposição do custo de equipamento (aquisição, depreciação,
-- manutenção, operação etc.), não só o total — informa decisões de
-- comprar/alugar equipamento.
select
    dim_insumo.codigo,
    dim_insumo.descricao,
    dim_uf.state_slug,
    dim_uf.state_name,
    dim_uf.region,
    fato_custo_equipamento.period_start,
    fato_custo_equipamento.desonerado,
    fato_custo_equipamento.valor_aquisicao,
    fato_custo_equipamento.depreciacao,
    fato_custo_equipamento.oportunidade_capital,
    fato_custo_equipamento.seguros_impostos,
    fato_custo_equipamento.manutencao,
    fato_custo_equipamento.operacao,
    fato_custo_equipamento.mao_de_obra_operacao,
    fato_custo_equipamento.custo_produtivo,
    fato_custo_equipamento.custo_improdutivo
from {{ ref('fato_custo_equipamento') }} as fato_custo_equipamento
inner join {{ ref('dim_insumo') }} as dim_insumo on fato_custo_equipamento.insumo_id = dim_insumo.insumo_id
inner join {{ ref('dim_uf') }} as dim_uf on fato_custo_equipamento.state_slug = dim_uf.state_slug
