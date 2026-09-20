# SICRO Relatório Sintético — data cleaning notes

Issues found while parsing raw SICRO Relatório Sintético xlsx files into
silver Parquet (`sources/sicro/reader.py`). Kept here because these
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

## 6. The same `codigo` can appear more than once within a single file, with fully identical values

Confirmed on `centro-oeste/distrito-federal/2021/outubro/df-outubro-2021/DF 10-2021
Relatório Sintético de Equipamentos - com desoneração.xlsx`: code `A9308`
("Caminhão plataforma 4 x 2... Motorista de veículo especial") appears 3
times (Excel rows 497, 504, 515), byte-identical across all 11 columns each
time — not a parsing bug, the source file itself lists it 3 times.

There's no section-header row anywhere in the sheet to explain this (every
row's first cell matches the `letra+dígitos` code pattern, confirmed by
scanning the whole sheet). The only pattern found: from roughly row 361 to
the end, the sheet is mostly `E9xxx`-coded items that only populate
`custo_produtivo`/`custo_improdutivo` (columns C:I merged/blank in Excel),
and `A9308` — which *does* have the full cost breakdown — is interspersed 3
times in that stretch, each time right after a different `E9xxx` row.
Likely explanation: this "synthetic" report is assembled from several
underlying cost compositions, and a shared support vehicle like A9308 gets
pulled in once per composition that references it, without dedup on the
DNIT side — but nothing in the file itself confirms this; it's inferred
from the position pattern, not stated data.

**Decision:** silver stays an untouched mirror of the source file, including
this duplication — `reader.py`/`writer.py` are not changed for this.
Deduplication (exact-duplicate rows here, and resolving `revisado` in
general) belongs in the dbt marts layer (`layers/gold_dbt/models/marts/facts/`),
as an explicit business-logic step over silver — not silently baked into the
parse pipeline. Implemented in `fato_preco_material`/`fato_custo_equipamento`/
`fato_custo_mao_de_obra` (see each model's header comment).

## General pattern

All of the above are handled in `reader.py` by failing loudly on anything
unrecognized (unknown header → `ValueError`, unexpected non-numeric value →
`ValueError` from `astype(float)`) rather than silently coercing/skipping.
When a new file trips one of these, prefer widening the known-good cases
(like `'-'` above) over broadening the coercion — that keeps bad data from
being an ambiguous decision.
