-- SICRO dropped salario/encargos_totais/periculosidade_insalubridade from
-- this report partway through 2025 (see REPORT_SCHEMAS in
-- connectors/sicro/parse/reader.py), so files from before and after that
-- change sit in the same source glob with different columns. union_by_name
-- on the source fills the missing ones with null rather than erroring;
-- schema_version makes which layout a row came from explicit instead of
-- leaving null-vs-populated as an implicit signal.
select
    -- DNIT não é consistente com maiúscula/minúscula no código do insumo
    -- entre publicações (ex: "A9299" numa tabela, "a9299" noutra) — sem
    -- padronizar aqui, o mesmo insumo vira duas linhas distintas em
    -- dim_insumo (group by tipo, codigo) e dois insumo_id diferentes nos
    -- fatos.
    lower(codigo) as codigo,
    -- SICRO publica a descrição toda em minúsculo — só a primeira letra
    -- maiúscula, resto minúsculo (não é Title Case por palavra).
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
