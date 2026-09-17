-- Warning (doesn't block the build) — flags UF/tipo with period gaps vs.
-- peer UFs (see vw_cobertura.sql), for ongoing visibility into how
-- up-to-date the gold is.
{{ config(severity = 'warn') }}

select *
from {{ ref('vw_cobertura') }}
where periodos_faltantes_vs_pares > 0
