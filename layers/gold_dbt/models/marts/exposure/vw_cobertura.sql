-- Q9: latest update per UF/tipo and gaps. "Gap" is relative to peer UFs, not
-- to an official DNIT calendar (not a source available here) —
-- periodos_esperados is any (tipo, period) where at least one UF actually
-- published.
with periodos as (
    select 'materiais' as tipo, state_slug, period_start from {{ ref('fato_preco_material') }}
    union
    select 'equipamentos' as tipo, state_slug, period_start from {{ ref('fato_custo_equipamento') }}
    union
    select 'mao_de_obra' as tipo, state_slug, period_start from {{ ref('fato_custo_mao_de_obra') }}
),

periodos_esperados as (
    select distinct tipo, period_start
    from periodos
),

todas_ufs as (
    select distinct state_slug from {{ ref('dim_uf') }}
),

periodos_faltantes as (
    select
        periodos_esperados.tipo,
        todas_ufs.state_slug,
        periodos_esperados.period_start
    from periodos_esperados
    cross join todas_ufs
    left join periodos as real
        on  periodos_esperados.tipo         = real.tipo
        and periodos_esperados.period_start = real.period_start
        and todas_ufs.state_slug            = real.state_slug
    where real.state_slug is null
),

contagem_faltantes as (
    select tipo, state_slug, count(*) as periodos_faltantes_vs_pares
    from periodos_faltantes
    group by 1, 2
),

ultimo_por_uf as (
    select
        tipo, state_slug,
        max(period_start) as ultimo_periodo_disponivel,
        count(distinct period_start) as periodos_disponiveis
    from periodos
    group by 1, 2
)

select
    ultimo_por_uf.tipo,
    dim_uf.state_slug,
    dim_uf.state_code,
    dim_uf.state_name,
    ultimo_por_uf.ultimo_periodo_disponivel,
    ultimo_por_uf.periodos_disponiveis,
    coalesce(contagem_faltantes.periodos_faltantes_vs_pares, 0) as periodos_faltantes_vs_pares
from ultimo_por_uf
inner join {{ ref('dim_uf') }} as dim_uf on ultimo_por_uf.state_slug = dim_uf.state_slug
left join contagem_faltantes
    on  ultimo_por_uf.tipo       = contagem_faltantes.tipo
    and ultimo_por_uf.state_slug = contagem_faltantes.state_slug
order by tipo, state_slug
