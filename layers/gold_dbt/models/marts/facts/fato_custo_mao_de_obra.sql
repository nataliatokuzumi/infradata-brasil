{{ config(
    materialized='incremental',
    unique_key='custo_mao_de_obra_id',
    incremental_strategy='delete+insert'
) }}

-- Grain: insumo (mao_de_obra) x UF x period x tax regime.
-- See fato_preco_material.sql for the rationale behind the incremental-by-
-- partition pattern and the `revisado` resolution — identical here, with
-- desonerado as part of the partition key. schema_version is passed through
-- as-is from staging (see stg_sicro__mao_de_obra.sql):
-- salario/encargos_totais/periculosidade_insalubridade only exist for
-- schema_version = 'pre_2025'.

with changed_partitions as (
    select distinct state_slug, year, month, desonerado
    from {{ ref('stg_sicro__mao_de_obra') }}
    {% if is_incremental() %}
    where parsed_at > (select coalesce(max(parsed_at), '1900-01-01'::timestamp) from {{ this }})
    {% endif %}
),

deduped as (
    select distinct staging.*
    from {{ ref('stg_sicro__mao_de_obra') }} as staging
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
    md5(concat_ws('|', 'mao_de_obra', resolved.codigo, resolved.state_slug, resolved.year, resolved.month, resolved.desonerado)) as custo_mao_de_obra_id,
    md5(concat_ws('|', 'mao_de_obra', resolved.codigo)) as insumo_id,
    resolved.state_slug,
    make_date(resolved.year, seed_month.month_number, 1) as period_start,
    resolved.desonerado,
    resolved.salario,
    resolved.encargos_totais,
    resolved.custo,
    resolved.periculosidade_insalubridade,
    resolved.schema_version,
    resolved.revisado,
    resolved.blob_name,
    resolved.parsed_at
from resolved
left join {{ ref('seed_month') }} as seed_month
    on resolved.month = seed_month.month_name
