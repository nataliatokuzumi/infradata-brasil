-- SICRO dropped salario/encargos_totais/periculosidade_insalubridade from
-- this report partway through 2025 (see REPORT_SCHEMAS in
-- connectors/sicro/parse/reader.py), so files from before and after that
-- change sit in the same source glob with different columns. union_by_name
-- on the source fills the missing ones with null rather than erroring;
-- schema_version makes which layout a row came from explicit instead of
-- leaving null-vs-populated as an implicit signal.
select
    codigo,
    descricao,
    unidade,
    salario,
    encargos_totais,
    custo,
    periculosidade_insalubridade,
    case
        when salario is not null then 'pre_2025'
        else '2025_plus'
    end as schema_version,
    report_type,
    desonerado,
    revisado,
    region,
    state_slug,
    cast(year as integer) as year,
    month,
    archive_stem,
    blob_name,
    cast(parsed_at as timestamp) as parsed_at
from {{ source('sicro_silver', 'mao_de_obra') }}
