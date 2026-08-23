select
    codigo,
    descricao,
    unidade,
    preco_unitario,
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
from {{ source('sicro_silver', 'materiais') }}
