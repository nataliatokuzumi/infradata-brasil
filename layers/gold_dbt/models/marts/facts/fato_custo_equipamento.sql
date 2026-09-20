{{ config(
    materialized='incremental',
    unique_key='custo_equipamento_id',
    incremental_strategy='delete+insert'
) }}

-- Grain: insumo (equipamentos) x UF x period x tax regime.
-- See fato_preco_material.sql for the rationale behind the incremental-by-
-- partition pattern and the `revisado` resolution — identical here, with
-- desonerado as part of the partition key.

with changed_partitions as (
    select distinct state_slug, year, month, desonerado
    from {{ ref('stg_sicro__equipamentos') }}
    {% if is_incremental() %}
    where parsed_at > (select coalesce(max(parsed_at), '1900-01-01'::timestamp) from {{ this }})
    {% endif %}
),

deduped as (
    select distinct staging.*
    from {{ ref('stg_sicro__equipamentos') }} as staging
    inner join changed_partitions
        on  staging.state_slug  = changed_partitions.state_slug
        and staging.year        = changed_partitions.year
        and staging.month       = changed_partitions.month
        and staging.desonerado  = changed_partitions.desonerado
),

revisado_periods as (
    select distinct state_slug, year, month, desonerado
    from deduped
    where revisado
),

resolved as (
    select deduped.*
    from deduped
    left join revisado_periods
        on  deduped.state_slug  = revisado_periods.state_slug
        and deduped.year        = revisado_periods.year
        and deduped.month       = revisado_periods.month
        and deduped.desonerado  = revisado_periods.desonerado
    where deduped.revisado or revisado_periods.state_slug is null
)

select
    md5(concat_ws('|', 'equipamentos', resolved.codigo, resolved.state_slug, resolved.year, resolved.month, resolved.desonerado)) as custo_equipamento_id,
    md5(concat_ws('|', 'equipamentos', resolved.codigo)) as insumo_id,
    resolved.state_slug,
    make_date(resolved.year, seed_month.month_number, 1) as period_start,
    resolved.desonerado,
    resolved.valor_aquisicao,
    resolved.depreciacao,
    resolved.oportunidade_capital,
    resolved.seguros_impostos,
    resolved.manutencao,
    resolved.operacao,
    resolved.mao_de_obra_operacao,
    resolved.custo_produtivo,
    resolved.custo_improdutivo,
    resolved.revisado,
    resolved.blob_name,
    resolved.parsed_at
from resolved
left join {{ ref('seed_month') }} as seed_month
    on resolved.month = seed_month.month_name
