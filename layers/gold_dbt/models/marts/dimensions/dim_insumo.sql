-- Grain: 1 row per (tipo, codigo) — item catalog across the three reports.
-- Uses arg_max(..., parsed_at) instead of plain distinct because, in theory,
-- descricao/unidade could vary between publications of the same code (not
-- confirmed as happening today, but not safe to assume it never will) —
-- arg_max guarantees a unique grain by taking the most recently known
-- label, instead of breaking if that ever changes.
with materiais as (
    select 'materiais' as tipo, codigo, descricao, unidade, parsed_at
    from {{ ref('stg_sicro__materiais') }}
),

equipamentos as (
    select 'equipamentos' as tipo, codigo, descricao, cast(null as varchar) as unidade, parsed_at
    from {{ ref('stg_sicro__equipamentos') }}
),

mao_de_obra as (
    select 'mao_de_obra' as tipo, codigo, descricao, unidade, parsed_at
    from {{ ref('stg_sicro__mao_de_obra') }}
),

unioned as (
    select * from materiais
    union all
    select * from equipamentos
    union all
    select * from mao_de_obra
)

select
    md5(concat_ws('|', tipo, codigo)) as insumo_id,
    tipo,
    codigo,
    arg_max(descricao, parsed_at) as descricao,
    arg_max(unidade, parsed_at) as unidade
from unioned
group by tipo, codigo
