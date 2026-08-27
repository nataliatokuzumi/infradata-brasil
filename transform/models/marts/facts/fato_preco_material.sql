{{ config(
    materialized='incremental',
    unique_key='preco_material_id',
    incremental_strategy='delete+insert'
) }}

-- Grão: insumo (materiais) x UF x período. Sem regime tributário —
-- confirmado que materiais não tem variante desonerado (silver sempre
-- reporta desonerado=false pra esse tipo, sem exceção observada).
--
-- Incremental por partição (UF x ano x mês): a cada rodada, só reprocessa
-- partições que tiveram alguma linha nova/mais recente na silver (via
-- parsed_at). Precisa reler a partição inteira, não só as linhas novas,
-- porque a resolução de `revisado` (docs/sicro_data_cleaning.md #6) precisa
-- ver as versões revisado=true/false lado a lado pra decidir qual manter —
-- por isso "changed_partitions" primeiro identifica QUAIS partições mudaram,
-- e "deduped" pega essas partições por inteiro.

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
