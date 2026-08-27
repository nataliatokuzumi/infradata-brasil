-- Grão: 1 linha por (tipo, codigo) — catálogo de itens across os três
-- relatórios. Usa arg_max(..., parsed_at) em vez de distinct puro porque, em
-- tese, descricao/unidade poderiam variar entre publicações do mesmo código
-- (não confirmado como acontecendo hoje, mas não é seguro assumir que nunca
-- vai acontecer) — arg_max garante grão único pegando o rótulo mais recente
-- conhecido, em vez de quebrar caso um dia isso mude.
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
