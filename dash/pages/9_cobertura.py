import dash
from dash import html

from components import data_table, page_header
from gold import TIPO_LABELS, formatar_periodo, query

# Desativada temporariamente pra focar o trabalho na página 1 — descomentar
# pra reativar.
# dash.register_page(__name__, path="/cobertura", name="9. Cobertura", title="Cobertura", order=9)


def layout(**kwargs):
    df = query(
        """
        select tipo, state_name, ultimo_periodo_disponivel, periodos_disponiveis, periodos_faltantes_vs_pares
        from vw_cobertura
        order by periodos_faltantes_vs_pares desc, tipo, state_name
        """
    )

    df_tabela = df.copy()
    df_tabela["tipo"] = df_tabela["tipo"].map(TIPO_LABELS)
    df_tabela["ultimo_periodo_disponivel"] = df_tabela["ultimo_periodo_disponivel"].apply(formatar_periodo)
    df_tabela = df_tabela.rename(
        columns={
            "tipo": "Tipo",
            "state_name": "UF",
            "ultimo_periodo_disponivel": "Última Publicação",
            "periodos_disponiveis": "Períodos Disponíveis",
            "periodos_faltantes_vs_pares": "Lacunas",
        }
    )

    style_data_conditional = [
        {
            "if": {"filter_query": "{Lacunas} > 0"},
            "backgroundColor": "var(--lacuna-bg)",
        }
    ]

    n_com_lacuna = int((df["periodos_faltantes_vs_pares"] > 0).sum())

    return html.Div(
        [
            *page_header(
                "Cobertura e Lacunas",
                "Última publicação por UF/tipo. 'Lacuna' é relativo às UFs pares, não "
                "a um calendário oficial do DNIT — Lacunas conta (tipo, período) em "
                "que ao menos uma UF publicou mas esta não.",
            ),
            data_table(df_tabela, style_data_conditional=style_data_conditional, page_size=len(df_tabela) or 1),
            html.P(f"{n_com_lacuna} de {len(df)} combinações (tipo, UF) têm alguma lacuna vs. as pares.", className="caption"),
        ]
    )
