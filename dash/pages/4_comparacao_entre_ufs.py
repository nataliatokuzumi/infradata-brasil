import dash
import plotly.express as px
from dash import Input, Output, callback, dcc, html

from components import data_table, filter_row, info_box, limpar_filtros_button, page_header
from gold import TIPO_LABELS, TIPOS, formatar_moeda_grafico, formatar_periodo, list_insumos, query, rotulo_medida, rotulo_regiao, rotulo_sim_nao


PREFIX = "cu"


def _buscar_por_codigo(codigo):
    return query(
        "select medida, desonerado, state_name, region, period_start, valor "
        "from vw_comparacao_uf where codigo = ?",
        [codigo],
    )


def layout(**kwargs):
    insumos = list_insumos(TIPOS[0])
    return html.Div(
        [
            *page_header("Comparação entre UFs", "Mesmo insumo, todas as UFs, no período mais recente disponível."),
            limpar_filtros_button(f"{PREFIX}-limpar"),
            filter_row(
                ("Tipo", dcc.Dropdown(
                    id=f"{PREFIX}-tipo",
                    options=[{"label": TIPO_LABELS[t], "value": t} for t in TIPOS],
                    value=TIPOS[0],
                    clearable=False,
                )),
                ("Insumo", dcc.Dropdown(
                    id=f"{PREFIX}-insumo",
                    options=[{"label": f"{row.descricao} ({row.codigo})", "value": row.codigo} for row in insumos.itertuples()],
                    value=insumos["codigo"].iloc[0] if not insumos.empty else None,
                    clearable=False,
                )),
            ),
            html.Div(id=f"{PREFIX}-medida-container"),
            html.Div(id=f"{PREFIX}-results"),
        ]
    )


@callback(
    Output(f"{PREFIX}-insumo", "options"),
    Output(f"{PREFIX}-insumo", "value"),
    Input(f"{PREFIX}-tipo", "value"),
)
def _atualizar_opcoes_insumo(tipo):
    insumos = list_insumos(tipo)
    opcoes = [{"label": f"{row.descricao} ({row.codigo})", "value": row.codigo} for row in insumos.itertuples()]
    valor_padrao = insumos["codigo"].iloc[0] if not insumos.empty else None
    return opcoes, valor_padrao


@callback(
    Output(f"{PREFIX}-tipo", "value"),
    Input(f"{PREFIX}-limpar", "n_clicks"),
    prevent_initial_call=True,
)
def _limpar_filtros(n_clicks):
    return TIPOS[0]


@callback(
    Output(f"{PREFIX}-medida-container", "children"),
    Input(f"{PREFIX}-insumo", "value"),
)
def _atualizar_medida(codigo):
    if not codigo:
        return info_box("Sem dados pra esse insumo.")

    df = _buscar_por_codigo(codigo)
    if df.empty:
        return info_box("Sem dados pra esse insumo.")

    opcoes_medida = sorted(df["medida"].unique())
    return html.Div([
        html.Label("Medida"),
        dcc.Dropdown(
            id=f"{PREFIX}-medida",
            options=[{"label": rotulo_medida(m), "value": m} for m in opcoes_medida],
            value=opcoes_medida[0],
            clearable=False,
        ),
    ])


@callback(
    Output(f"{PREFIX}-results", "children"),
    Input(f"{PREFIX}-insumo", "value"),
    Input(f"{PREFIX}-medida-container", "children"),
    Input(f"{PREFIX}-medida", "value"),
)
def _renderizar_resultados(codigo, _medida_container, medida):
    if not codigo or not medida:
        return None

    df = _buscar_por_codigo(codigo)
    if df.empty:
        return info_box("Sem dados pra esse insumo.")

    df_medida = df[df["medida"] == medida].copy()
    df_medida["region"] = df_medida["region"].map(rotulo_regiao)

    ultimo_periodo = df_medida["period_start"].max()
    df_periodo = df_medida[df_medida["period_start"] == ultimo_periodo].sort_values("valor", ascending=False).copy()
    df_periodo["rótulo"] = df_periodo["valor"].apply(formatar_moeda_grafico)

    fig = px.bar(df_periodo, x="state_name", y="valor", color="region", text="rótulo")
    fig.update_traces(hovertemplate="%{x}: %{text}<extra></extra>")
    fig.update_layout(xaxis_title="UF", yaxis_title="Valor (R$)", legend_title="Região")

    df_tabela = df_periodo[["state_name", "region", "desonerado", "valor"]].copy()
    df_tabela["desonerado"] = df_periodo["desonerado"].apply(rotulo_sim_nao)
    df_tabela["valor"] = df_periodo["valor"].apply(formatar_moeda_grafico)
    df_tabela = df_tabela.rename(
        columns={"state_name": "UF", "region": "Região", "desonerado": "Desonerado", "valor": "Valor"}
    )

    return [
        html.H3(f"Período: {formatar_periodo(ultimo_periodo)}", className="section-subheader"),
        dcc.Graph(figure=fig),
        data_table(df_tabela),
    ]
