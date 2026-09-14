import dash
import pandas as pd
import plotly.express as px
from dash import Input, Output, callback, dcc, html

from components import data_table, filter_row, info_box, limpar_filtros_button, metric_card, metric_row, page_header
from gold import (
    formatar_moeda,
    formatar_moeda_grafico,
    formatar_periodo,
    list_insumos,
    list_ufs,
    query,
    rotulo_medida,
    rotulo_regiao,
    rotulo_schema_version,
    rotulo_sim_nao,
)

# Desativada temporariamente pra focar o trabalho na página 1 — descomentar
# pra reativar.
# dash.register_page(
#     __name__,
#     path="/detalhamento-de-mao-de-obra",
#     name="8. Detalhamento de Mão de Obra",
#     title="Detalhamento de Mão de Obra",
#     order=8,
# )

PREFIX = "dm"

COLUNAS_EXIBICAO = {
    "codigo": "Código",
    "descricao": "Descrição",
    "unidade": "Unidade",
    "state_name": "UF",
    "region": "Região",
    "period_start": "Publicação",
    "desonerado": "Desonerado",
    "salario": "Salário",
    "encargos_totais": "Encargos Totais",
    "periculosidade_insalubridade": "Periculosidade e Insalubridade",
    "custo": "Custo Final",
    "schema_version": "Layout",
}


def _buscar_breakdown(codigo, slug):
    return query(
        "select * from vw_breakdown_mao_de_obra where codigo = ? and state_slug = ? order by period_start",
        [codigo, slug],
    )


def layout(**kwargs):
    insumos = list_insumos("mao_de_obra")
    ufs = list_ufs()
    return html.Div(
        [
            *page_header(
                "Detalhamento de Mão de Obra",
                "Salário/encargos/periculosidade só existem pra períodos até 2025 — a "
                "partir daí o SICRO passou a publicar só o custo final, sem "
                "detalhamento de componentes (ausência de dado, não zero).",
            ),
            limpar_filtros_button(f"{PREFIX}-limpar"),
            filter_row(
                ("Item de Mão de Obra", dcc.Dropdown(
                    id=f"{PREFIX}-item",
                    options=[{"label": f"{row.descricao} ({row.codigo})", "value": row.codigo} for row in insumos.itertuples()],
                    value=insumos["codigo"].iloc[0] if not insumos.empty else None,
                    clearable=False,
                )),
                ("UF", dcc.Dropdown(
                    id=f"{PREFIX}-uf",
                    options=[{"label": n, "value": n} for n in ufs["state_name"]],
                    value=ufs["state_name"].iloc[0] if not ufs.empty else None,
                    clearable=False,
                )),
            ),
            html.Div(id=f"{PREFIX}-periodo-container"),
            html.Div(id=f"{PREFIX}-results"),
        ]
    )


@callback(
    Output(f"{PREFIX}-item", "value"),
    Output(f"{PREFIX}-uf", "value"),
    Input(f"{PREFIX}-limpar", "n_clicks"),
    prevent_initial_call=True,
)
def _limpar_filtros(n_clicks):
    insumos = list_insumos("mao_de_obra")
    ufs = list_ufs()
    return (
        insumos["codigo"].iloc[0] if not insumos.empty else None,
        ufs["state_name"].iloc[0] if not ufs.empty else None,
    )


@callback(
    Output(f"{PREFIX}-periodo-container", "children"),
    Input(f"{PREFIX}-item", "value"),
    Input(f"{PREFIX}-uf", "value"),
)
def _atualizar_periodo(codigo, uf_escolhida):
    if not codigo or not uf_escolhida:
        return info_box("Sem dados pra essa combinação.")

    ufs = list_ufs()
    slug = ufs[ufs["state_name"] == uf_escolhida]["state_slug"].iloc[0]
    df = _buscar_breakdown(codigo, slug)

    if df.empty:
        return info_box("Sem dados pra essa combinação.")

    periodos = sorted(df["period_start"].unique(), reverse=True)
    return html.Div([
        html.Label("Período"),
        dcc.Dropdown(
            id=f"{PREFIX}-periodo",
            options=[{"label": formatar_periodo(p), "value": p.isoformat()} for p in periodos],
            value=periodos[0].isoformat(),
            clearable=False,
        ),
    ])


@callback(
    Output(f"{PREFIX}-results", "children"),
    Input(f"{PREFIX}-item", "value"),
    Input(f"{PREFIX}-uf", "value"),
    Input(f"{PREFIX}-periodo-container", "children"),
    Input(f"{PREFIX}-periodo", "value"),
)
def _renderizar_resultados(codigo, uf_escolhida, _periodo_container, periodo_iso):
    if not codigo or not uf_escolhida or not periodo_iso:
        return None

    ufs = list_ufs()
    slug = ufs[ufs["state_name"] == uf_escolhida]["state_slug"].iloc[0]
    df = _buscar_breakdown(codigo, slug)

    if df.empty:
        return info_box("Sem dados pra essa combinação.")

    df_periodo = df[df["period_start"] == pd.Timestamp(periodo_iso)]

    conteudo = []
    for _, row in df_periodo.iterrows():
        regime = "Desonerado" if row["desonerado"] else "Não Desonerado"
        conteudo.append(html.H3(f"{regime} — {rotulo_schema_version(row['schema_version'])}"))
        conteudo.append(metric_row(metric_card("Custo Final", formatar_moeda(row["custo"]))))
        if row["schema_version"] == "pre_2025":
            componentes = row[["salario", "encargos_totais", "periculosidade_insalubridade"]].reset_index()
            componentes.columns = ["componente", "valor"]
            componentes["componente"] = componentes["componente"].map(rotulo_medida)
            componentes["rótulo"] = componentes["valor"].apply(formatar_moeda_grafico)
            fig = px.bar(componentes, x="componente", y="valor", text="rótulo")
            fig.update_traces(hovertemplate="%{x}: %{text}<extra></extra>")
            fig.update_layout(xaxis_title="Componente", yaxis_title="Valor (R$)")
            conteudo.append(dcc.Graph(figure=fig))
        else:
            conteudo.append(html.P("Layout 2025+: SICRO só publica o custo final, sem detalhamento de componentes.", className="caption"))

    df_tabela = df[list(COLUNAS_EXIBICAO.keys())].copy()
    df_tabela["region"] = df["region"].map(rotulo_regiao)
    df_tabela["period_start"] = df["period_start"].apply(formatar_periodo)
    df_tabela["desonerado"] = df["desonerado"].apply(rotulo_sim_nao)
    df_tabela["unidade"] = df["unidade"].fillna("—")
    df_tabela["schema_version"] = df["schema_version"].apply(rotulo_schema_version)
    for col in ["salario", "encargos_totais", "periculosidade_insalubridade", "custo"]:
        df_tabela[col] = df[col].apply(lambda v: "—" if pd.isna(v) else formatar_moeda_grafico(v))
    df_tabela = df_tabela.rename(columns=COLUNAS_EXIBICAO)
    conteudo.append(data_table(df_tabela))

    return conteudo
