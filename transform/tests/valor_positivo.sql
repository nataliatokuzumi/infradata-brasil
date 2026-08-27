-- Todo valor em fato_medicao deve ser não-negativo (confirmado
-- empiricamente: 0 negativos em toda a silver atual). Estritamente positivo
-- (>0) só se aplica aos totais (preco_unitario, custo_produtivo,
-- custo_improdutivo, custo) — os componentes de custo (seguros_impostos,
-- operacao, mao_de_obra_operacao, periculosidade_insalubridade etc.) podem
-- legitimamente ser zero quando aquele item não incorre naquele componente
-- (confirmado: só aparecem zeros nesses componentes, nunca nos totais).
select *
from {{ ref('fato_medicao') }}
where valor < 0
   or (valor = 0 and medida in ('preco_unitario', 'custo_produtivo', 'custo_improdutivo', 'custo'))
