-- SICRO dropped salario/encargos_totais/periculosidade_insalubridade from
-- this report partway through 2025 (see REPORT_SCHEMAS in
-- connectors/sicro/parse/reader.py), so files from before and after that
-- change sit in the same source glob with different columns. union_by_name
-- on the source fills the missing ones with null rather than erroring;
-- schema_version makes which layout a row came from explicit instead of
-- leaving null-vs-populated as an implicit signal.
select
    -- DNIT isn't consistent about the case of the insumo code between
    -- publications (e.g. "A9299" in one table, "a9299" in another) —
    -- without standardizing this here, the same insumo turns into two
    -- distinct rows in dim_insumo (group by tipo, codigo) and two different
    -- insumo_id in the facts.
    lower(codigo) as codigo,
    -- SICRO publishes the description entirely in lowercase — only the
    -- first letter uppercase, the rest lowercase (not per-word Title Case).
    upper(substr(descricao, 1, 1)) || lower(substr(descricao, 2)) as descricao,
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
    -- desonerado is also a hive-partition-style path segment
    -- (desonerado=true/false/, see writer.py's build_silver_blob_name) —
    -- DuckDB's hive-partition inference reads that segment as text and
    -- shadows the real in-file boolean column, so this cast is needed even
    -- though the underlying value is genuinely a boolean.
    cast(desonerado as boolean) as desonerado,
    revisado,
    region,
    state_slug,
    cast(year as integer) as year,
    month,
    archive_stem,
    blob_name,
    cast(parsed_at as timestamp) as parsed_at
from {{ source('sicro_silver', 'mao_de_obra') }}
