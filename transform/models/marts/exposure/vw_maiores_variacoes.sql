-- Q6: maiores variações de preço/custo recentes — sinal de risco pra linhas
-- de orçamento que podem estourar. Top 20 por |variacao_percentual| em cada
-- (tipo, UF), avaliado no último período disponível daquela UF (UFs
-- publicam em cronogramas diferentes, ver vw_cobertura). Ajuste o corte
-- "posicao <= 20" abaixo pra alargar ou restringir a lista.
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
