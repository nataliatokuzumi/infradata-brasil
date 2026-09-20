{% macro export_to_gold() %}
{#
  Post-hook for every model under marts/: after the model builds, copy its
  full current state out to Parquet under gold/<model_name>/data.parquet in
  the same Azure Blob Storage container silver already lives in — same
  pattern (Blob Storage + external read_parquet), one level up. Runs after
  every build (full-refresh or incremental) so the export always reflects
  {{ this }}'s complete current contents, not just an incremental delta.
#}
copy (select * from {{ this }}) to 'azure://{{ env_var("AZURE_STORAGE_CONTAINER") }}/gold/{{ this.name }}/data.parquet' (format parquet)
{% endmacro %}
