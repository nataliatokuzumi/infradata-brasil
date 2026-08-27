-- Warning (não bloqueia o build) — sinaliza variações trimestre a trimestre
-- acima de 30% em vw_evolucao_preco, pra revisão manual. Uma variação
-- grande pode ser dado legítimo (ver docs/sicro_data_cleaning.md), então
-- isso é um alerta, não um erro. Ajuste o limiar de 0.3 conforme a
-- experiência real de uso mostrar o que é "normal" pra cada categoria.
{{ config(severity = 'warn') }}

select *
from {{ ref('vw_evolucao_preco') }}
where abs(variacao_percentual) > 0.3
