-- Grão: 1 linha por UF.
select
    state_slug,
    state_code,
    state_name,
    region
from {{ ref('seed_location') }}
