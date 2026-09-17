-- Grain: insumo x UF x period x regime x medida. "Long" fact — unpivots the
-- three wide facts (fato_preco_material/custo_equipamento/custo_mao_de_obra)
-- into a generic metric (`valor`), so cross-cutting questions (evolution,
-- reajuste index, biggest variations) don't need separate logic per type.
-- medida is 'preco_unitario' for materiais, 'custo_produtivo'/
-- 'valor_aquisicao'/etc. for equipamentos, 'salario'/'custo'/etc. for
-- mao_de_obra.
--
-- Not incremental: the three source facts already are (they're the
-- expensive part, since they read external parquet from Blob Storage);
-- rebuilding this unpivot in full every run is cheap (reads already-
-- materialized local tables) and avoids duplicating the "partition changed"
-- logic once more without need.

with material as (
    select
        preco_material_id as fato_id, insumo_id, state_slug, period_start,
        false as desonerado, revisado, blob_name, parsed_at,
        preco_unitario
    from {{ ref('fato_preco_material') }}
),

material_unpivoted as (
    unpivot material
    on preco_unitario
    into name medida value valor
),

equipamento as (
    select
        custo_equipamento_id as fato_id, insumo_id, state_slug, period_start,
        desonerado, revisado, blob_name, parsed_at,
        valor_aquisicao, depreciacao, oportunidade_capital, seguros_impostos,
        manutencao, operacao, mao_de_obra_operacao, custo_produtivo, custo_improdutivo
    from {{ ref('fato_custo_equipamento') }}
),

equipamento_unpivoted as (
    unpivot equipamento
    on valor_aquisicao, depreciacao, oportunidade_capital, seguros_impostos,
       manutencao, operacao, mao_de_obra_operacao, custo_produtivo, custo_improdutivo
    into name medida value valor
),

mao_de_obra as (
    select
        custo_mao_de_obra_id as fato_id, insumo_id, state_slug, period_start,
        desonerado, revisado, blob_name, parsed_at,
        salario, encargos_totais, custo, periculosidade_insalubridade
    from {{ ref('fato_custo_mao_de_obra') }}
),

mao_de_obra_unpivoted as (
    unpivot mao_de_obra
    on salario, encargos_totais, custo, periculosidade_insalubridade
    into name medida value valor
),

unioned as (
    select * from material_unpivoted
    union all
    select * from equipamento_unpivoted
    union all
    select * from mao_de_obra_unpivoted
)

select
    md5(concat_ws('|', fato_id, medida)) as medicao_id,
    insumo_id,
    state_slug,
    period_start,
    desonerado,
    medida,
    valor,
    revisado,
    blob_name,
    parsed_at
from unioned
where valor is not null
