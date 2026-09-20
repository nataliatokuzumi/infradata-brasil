-- Q6: biggest recent price/cost variations — a risk signal for budget lines
-- that might blow out. Top 20 by |variacao_percentual| within each (tipo,
-- UF), evaluated at that UF's latest available period (UFs publish on
-- different schedules, see vw_cobertura). Adjust the "posicao <= 20" cutoff
-- below to widen or narrow the list.
with evolucao as (
    select * from {{ ref('vw_evolucao_preco') }}
    where variacao_percentual is not null
),

ultimo_periodo as (
    select tipo, state_slug, max(period_start) as ultimo_period_start
    from evolucao
    group by 1, 2
),

apenas_ultimo as (
    select evolucao.*
    from evolucao
    inner join ultimo_periodo
        on  evolucao.tipo         = ultimo_periodo.tipo
        and evolucao.state_slug   = ultimo_periodo.state_slug
        and evolucao.period_start = ultimo_periodo.ultimo_period_start
),

ranqueado as (
    select
        *,
        row_number() over (
            partition by tipo, state_slug
            order by abs(variacao_percentual) desc
        ) as posicao
    from apenas_ultimo
)

select *
from ranqueado
where posicao <= 20
order by tipo, state_slug, posicao
