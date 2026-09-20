import dash
import pandas as pd
import plotly.express as px
from dash import Input, Output, callback, dcc, html

from components import data_table, filter_row, info_box, limpar_filtros_button, metric_card, metric_row, page_header
from gold import formatar_moeda, formatar_moeda_grafico, formatar_periodo, list_insumos, list_ufs, query, rotulo_medida, rotulo_regiao, rotulo_sim_nao


PREFIX = "de"

COMPONENTES = [
    "valor_aquisicao",
    "depreciacao",
    "oportunidade_capital",
    "seguros_impostos",
    "manutencao",
    "operacao",
    "mao_de_obra_operacao",
]

COLUNAS_EXIBICAO = {
    "codigo": "Código",
    "descricao": "Descrição",
    "state_name": "UF",
    "region": "Região",
    "period_start": "Publicação",
    "desonerado": "Desonerado",
    "valor_aquisicao": "Valor de Aquisição",
    "depreciacao": "Depreciação",
    "oportunidade_capital": "Oportunidade de Capital",
    "seguros_impostos": "Seguros e Impostos",
    "manutencao": "Manutenção",
    "operacao": "Operação",
    "mao_de_obra_operacao": "Mão de Obra de Operação",
    "custo_produtivo": "Custo Produtivo",
    "custo_improdutivo": "Custo Improdutivo",
}


def _buscar_breakdown(codigo, slug):
    return query(
        "select * from vw_breakdown_equipamento where codigo = ? and state_slug = ? order by period_start",
        [codigo, slug],
    )


def layout(**kwargs):
    insumos = list_insumos("equipamentos")
    ufs = list_ufs()
    return html.Div(
        [
            *page_header("Detalhamento de Equipamento", "Não só o total: de onde vem o custo de um equipamento."),
            limpar_filtros_button(f"{PREFIX}-limpar"),
            filter_row(
                ("Equipamento", dcc.Dropdown(
                    id=f"{PREFIX}-equip",
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
    Output(f"{PREFIX}-equip", "value"),
    Output(f"{PREFIX}-uf", "value"),
    Input(f"{PREFIX}-limpar", "n_clicks"),
    prevent_initial_call=True,
)
def _limpar_filtros(n_clicks):
    insumos = list_insumos("equipamentos")
    ufs = list_ufs()
    return (
        insumos["codigo"].iloc[0] if not insumos.empty else None,
        ufs["state_name"].iloc[0] if not ufs.empty else None,
    )


@callback(
    Output(f"{PREFIX}-periodo-container", "children"),
    Input(f"{PREFIX}-equip", "value"),
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
    Input(f"{PREFIX}-equip", "value"),
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
        conteudo.append(html.H3(regime))
        componentes_df = row[COMPONENTES].reset_index()
        componentes_df.columns = ["componente", "valor"]
        componentes_df["componente"] = componentes_df["componente"].map(rotulo_medida)
        componentes_df["rótulo"] = componentes_df["valor"].apply(formatar_moeda_grafico)
        fig = px.bar(componentes_df, x="componente", y="valor", text="rótulo")
        fig.update_traces(hovertemplate="%{x}: %{text}<extra></extra>")
        fig.update_layout(xaxis_title="Componente", yaxis_title="Valor (R$)")
        conteudo.append(dcc.Graph(figure=fig))
        conteudo.append(
            metric_row(
                metric_card("Custo Produtivo (CHP)", formatar_moeda(row["custo_produtivo"])),
                metric_card("Custo Improdutivo (CHI)", formatar_moeda(row["custo_improdutivo"])),
            )
        )

    df_tabela = df[list(COLUNAS_EXIBICAO.keys())].copy()
    df_tabela["region"] = df["region"].map(rotulo_regiao)
    df_tabela["period_start"] = df["period_start"].apply(formatar_periodo)
    df_tabela["desonerado"] = df["desonerado"].apply(rotulo_sim_nao)
    for col in COMPONENTES + ["custo_produtivo", "custo_improdutivo"]:
        df_tabela[col] = df[col].apply(formatar_moeda_grafico)
    df_tabela = df_tabela.rename(columns=COLUNAS_EXIBICAO)
    conteudo.append(data_table(df_tabela))

    return conteudo
