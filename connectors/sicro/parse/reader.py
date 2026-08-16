from io import BytesIO

import openpyxl
import pandas as pd

# Confirmed by opening a real "Relatório Sintético de Materiais.xlsx" from
# blob storage: single sheet, this exact header row, one row per item.
EXPECTED_HEADER = ("Código", "Descrição", "Unidade", "Preço Unitário\n(R$)")
COLUMNS = ("codigo", "descricao", "unidade", "preco_unitario")


def parse_relatorio_sintetico(xlsx_bytes: bytes) -> pd.DataFrame:
    """Parses a Relatório Sintético xlsx (Materiais/Equipamentos/Mão de Obra)
    into a flat DataFrame. Raises ValueError on an unexpected header instead
    of silently skipping/guessing — a bad file becomes a 'failed' tracking
    row upstream, matching SicroClient._process_row's fail-loudly convention."""

    workbook = openpyxl.load_workbook(BytesIO(xlsx_bytes), data_only=True)
    worksheet = workbook[workbook.sheetnames[0]]

    rows = worksheet.iter_rows(values_only=True)
    header = next(rows, None)

    if header != EXPECTED_HEADER:
        raise ValueError(
            f"Unexpected header {header!r} in Relatório Sintético xlsx, "
            f"expected {EXPECTED_HEADER!r}"
        )

    data = [row for row in rows if row and row[0] is not None]

    df = pd.DataFrame(data, columns=COLUMNS)
    df["codigo"] = df["codigo"].astype(str).str.strip()
    df["descricao"] = df["descricao"].astype(str).str.strip()
    df["unidade"] = df["unidade"].astype(str).str.strip()
    df["preco_unitario"] = df["preco_unitario"].astype(float)

    return df
