-- Grain: 1 row per UF (Brazilian state).
select
    state_slug,
    state_code,
    state_name,
    region
from {{ ref('seed_location') }}
