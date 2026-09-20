{{ config(
    materialized='incremental',
    unique_key='preco_material_id',
    incremental_strategy='delete+insert'
) }}

-- Grain: insumo (materiais) x UF x period. No tax regime — confirmed that
-- materiais has no desonerado variant (silver always reports
-- desonerado=false for this type, no exception observed).
--
-- Incremental by partition (UF x year x month): each run only reprocesses
-- partitions that had some new/more recent row in silver (via parsed_at).
-- Needs to reread the whole partition, not just the new rows, because
-- resolving `revisado` (docs/sicro_data_cleaning.md #6) needs to see the
-- revisado=true/false versions side by side to decide which to keep — that's
-- why "changed_partitions" first identifies WHICH partitions changed, and
-- "deduped" pulls those partitions in full.

with changed_partitions as (
    select distinct state_slug, year, month
    from {{ ref('stg_sicro__materiais') }}
    {% if is_incremental() %}
    where parsed_at > (select coalesce(max(parsed_at), '1900-01-01'::timestamp) from {{ this }})
    {% endif %}
),

deduped as (
    select distinct staging.*
    from {{ ref('stg_sicro__materiais') }} as staging
    inner join changed_partitions
        on  staging.state_slug = changed_partitions.state_slug
        and staging.year       = changed_partitions.year
        and staging.month      = changed_partitions.month
),

revisado_periods as (
    select distinct state_slug, year, month
    from deduped
    where revisado
),

resolved as (
    select deduped.*
    from deduped
    left join revisado_periods
        on  deduped.state_slug = revisado_periods.state_slug
        and deduped.year       = revisado_periods.year
        and deduped.month      = revisado_periods.month
    where deduped.revisado or revisado_periods.state_slug is null
)

select
    md5(concat_ws('|', 'materiais', resolved.codigo, resolved.state_slug, resolved.year, resolved.month)) as preco_material_id,
    md5(concat_ws('|', 'materiais', resolved.codigo)) as insumo_id,
    resolved.state_slug,
    make_date(resolved.year, seed_month.month_number, 1) as period_start,
    resolved.preco_unitario,
    resolved.revisado,
    resolved.blob_name,
    resolved.parsed_at
from resolved
left join {{ ref('seed_month') }} as seed_month
    on resolved.month = seed_month.month_name
