-- Q2: evolution of an insumo/medida over time, by UF/regime.
-- valor_anterior/variacao_percentual are null for the first period observed
-- in a series — there's nothing to compare against yet.
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
-- Clusters rows physically by (tipo, medida, state_slug) before export_to_gold
-- writes this out to a single unpartitioned Parquet file (see
-- macros/export_to_gold.sql) — dash's vw_evolucao_preco query
-- (dash/pages/6_maiores_variacoes.py) filters on exactly these columns
-- (tipo =, medida =, state_slug in (...)); without this ordering the rows
-- for a given filter are scattered across every row group, forcing DuckDB
-- to read most of the ~4.4M-row file from Blob per query — with this
-- ordering, row-group min/max stats let it skip most of the file.
order by tipo, medida, state_slug, period_start
