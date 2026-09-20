-- Warning (doesn't block the build) — flags quarter-over-quarter variations
-- above 30% in vw_evolucao_preco, for manual review. A large variation can
-- be legitimate data (see docs/sicro_data_cleaning.md), so this is an
-- alert, not an error. Adjust the 0.3 threshold as real usage experience
-- shows what's "normal" for each category.
{{ config(severity = 'warn') }}

select *
from {{ ref('vw_evolucao_preco') }}
where abs(variacao_percentual) > 0.3
