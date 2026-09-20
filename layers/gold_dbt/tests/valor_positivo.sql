-- Every value in fato_medicao must be non-negative (confirmed empirically:
-- 0 negatives across all current silver data). Strictly positive (>0) only
-- applies to the totals (preco_unitario, custo_produtivo, custo_improdutivo,
-- custo) — the cost components (seguros_impostos, operacao,
-- mao_de_obra_operacao, periculosidade_insalubridade etc.) can legitimately
-- be zero when that item doesn't incur that component (confirmed: zeros
-- only appear in those components, never in the totals).
select *
from {{ ref('fato_medicao') }}
where valor < 0
   or (valor = 0 and medida in ('preco_unitario', 'custo_produtivo', 'custo_improdutivo', 'custo'))
