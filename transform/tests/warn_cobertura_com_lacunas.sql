-- Warning (não bloqueia o build) — sinaliza UF/tipo com lacunas de período
-- vs. as UFs pares (ver vw_cobertura.sql), pra visibilidade contínua sobre
-- quão atualizada a gold está.
{{ config(severity = 'warn') }}

select *
from {{ ref('vw_cobertura') }}
where periodos_faltantes_vs_pares > 0
