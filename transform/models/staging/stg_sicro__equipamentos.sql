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
    valor_aquisicao,
    depreciacao,
    oportunidade_capital,
    seguros_impostos,
    manutencao,
    operacao,
    mao_de_obra_operacao,
    custo_produtivo,
    custo_improdutivo,
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
from {{ source('sicro_silver', 'equipamentos') }}
