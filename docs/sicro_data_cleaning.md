# SICRO Relatório Sintético — data cleaning notes

Issues found while parsing raw SICRO Relatório Sintético xlsx files into
silver Parquet (`connectors/sicro/parse/reader.py`). Kept here because these
are quirks in the source files themselves — they'll resurface as more
files/states/years get parsed, not one-off bugs.

## 1. Header isn't always row 1

Files carry a title/metadata banner before the real column header, e.g.:

```
('CGCIT', 'SISTEMA DE CUSTOS REFERENCIAIS DE OBRAS - SICRO', ..., 'DNIT')
(None, 'Distrito Federal - Outubro/2021', None, None)
('Código', 'Descrição', 'Unidade', 'Preço Unitário (R$)')   <- real header
```

Fix: scan rows for the header instead of assuming row 1.

## 2. Column schema differs per report type

`EXPECTED_HEADER` was only ever confirmed against a Materiais file. Equipamentos
and Mão de Obra have entirely different columns — not a subset/superset, a
different shape:

| report_type   | columns |
|---------------|---------|
| materiais     | codigo, descricao, unidade, preco_unitario |
| equipamentos  | codigo, descricao, valor_aquisicao, depreciacao, oportunidade_capital, seguros_impostos, manutencao, operacao, mao_de_obra_operacao, custo_produtivo, custo_improdutivo |
| mao_de_obra   | codigo, descricao, unidade, salario, encargos_totais, custo, periculosidade_insalubridade |

Fix: `REPORT_SCHEMAS` dict keyed by `report_type`, each with its own expected
header + column names. `parse_relatorio_sintetico` now takes `report_type` as
an argument. Silver output is already partitioned by `report_type`
(`writer.py`), so the differing schemas don't need to be reconciled into one
shape.

## 3. Header whitespace is inconsistent across files

Same logical header, different literal bytes:

```
"Preço Unitário\n(R$)"   # newline
"Preço Unitário (R$)"    # space
```

Fix: normalize whitespace (collapse all runs of whitespace, including
newlines, to a single space) on both the expected header and each row before
comparing.

## 4. Data string columns need standardizing

`codigo`, `descricao`, `unidade` values vary in casing/whitespace across
files even when they refer to the same real-world thing. Fix: lowercase,
strip, and collapse internal whitespace on every string data column
(`_clean_string`), not just the header.

## 5. Numeric columns use `'-'` as a "no value" placeholder

Some numeric cells contain the literal string `'-'` instead of being blank,
which breaks a plain `astype(float)`. Fix: map `'-'` to `None` before casting
(`_clean_numeric`) — anything else non-numeric still raises, keeping the
fail-loudly convention (a bad file becomes a `status: failed` tracking row
rather than silently mis-parsing).

## General pattern

All of the above are handled in `reader.py` by failing loudly on anything
unrecognized (unknown header → `ValueError`, unexpected non-numeric value →
`ValueError` from `astype(float)`) rather than silently coercing/skipping.
When a new file trips one of these, prefer widening the known-good cases
(like `'-'` above) over broadening the coercion — that keeps bad data from
being an ambiguous decision.
