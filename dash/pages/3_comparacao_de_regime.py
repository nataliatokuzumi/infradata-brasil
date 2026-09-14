import dash
import pandas as pd
import plotly.express as px
from dash import Input, Output, callback, dcc, html

from components import data_table, filter_row, info_box, limpar_filtros_button, page_header
from gold import MEDIDA_PRINCIPAL, TIPO_LABELS, formatar_moeda_grafico, formatar_periodo, list_insumos, list_ufs, query, rotulo_medida

# Desativada temporariamente pra focar o trabalho na página 1 — descomentar
# pra reativar.
# dash.register_page(__name__, path="/comparacao-de-regime", name="3. Comparação de Regime", title="Comparação de Regime", order=3)

PREFIX = "cr"
TIPOS_REGIME = ["equipamentos", "mao_de_obra"]


def _buscar_comparacao(tipo, codigo_descricao, codigo_escolhido, ufs_escolhidas):
    sql = """
        select codigo, medida, state_name, period_start, valor_desonerado, valor_nao_desonerado, diferenca_percentual
        from vw_comparacao_regime
        where tipo = ?
    """
    params: list = [tipo]

    if codigo_descricao != "Todas":
        sql += " and codigo = ?"
        params.append(codigo_descricao)

    if codigo_escolhido != "Todos":
        sql += " and codigo = ?"
        params.append(codigo_escolhido)

    if ufs_escolhidas:
        placeholders = ",".join(["?"] * len(ufs_escolhidas))
        sql += f" and state_name in ({placeholders})"
        params.extend(ufs_escolhidas)

    sql += " order by medida, period_start"

    df = query(sql, params)

    if df.empty:
        return df, "Sem dados pra essa combinação de filtros."

    if df["codigo"].nunique() > 1:
        return df.iloc[0:0], "Escolha uma Descrição (ou Código) específica pra ver a comparação de regime."

    return df, None


def layout(**kwargs):
    ufs = list_ufs()
    return html.Div(
        [
            *page_header(
                "Comparação de Regime",
                "Materiais não aparece aqui — SICRO não publica variante desonerado pra preço de material.",
            ),
            limpar_filtros_button(f"{PREFIX}-limpar"),
            filter_row(
                ("Tipo", dcc.Dropdown(
                    id=f"{PREFIX}-tipo",
                    options=[{"label": TIPO_LABELS[t], "value": t} for t in TIPOS_REGIME],
                    value=TIPOS_REGIME[0],
                    clearable=False,
                )),
                ("Descrição", dcc.Dropdown(id=f"{PREFIX}-descricao", value="Todas", clearable=False)),
                ("Código", dcc.Dropdown(id=f"{PREFIX}-codigo", value="Todos", clearable=False)),
                ("UFs (vazio = todas)", dcc.Dropdown(
                    id=f"{PREFIX}-uf",
                    options=[{"label": n, "value": n} for n in ufs["state_name"]],
                    value=[],
                    multi=True,
                )),
            ),
            html.Div(id=f"{PREFIX}-medida-container"),
            html.Div(id=f"{PREFIX}-results"),
        ]
    )


@callback(
    Output(f"{PREFIX}-descricao", "options"),
    Output(f"{PREFIX}-codigo", "options"),
    Input(f"{PREFIX}-tipo", "value"),
)
def _atualizar_opcoes_insumo(tipo):
    insumos = list_insumos(tipo)
    opcoes_descricao = [{"label": "Todas", "value": "Todas"}] + [
        {"label": f"{row.descricao} ({row.codigo})", "value": row.codigo} for row in insumos.itertuples()
    ]
    opcoes_codigo = [{"label": "Todos", "value": "Todos"}] + [
        {"label": c, "value": c} for c in sorted(insumos["codigo"].tolist())
    ]
    return opcoes_descricao, opcoes_codigo


@callback(
    Output(f"{PREFIX}-tipo", "value"),
    Output(f"{PREFIX}-descricao", "value"),
    Output(f"{PREFIX}-codigo", "value"),
    Output(f"{PREFIX}-uf", "value"),
    Input(f"{PREFIX}-limpar", "n_clicks"),
    prevent_initial_call=True,
)
def _limpar_filtros(n_clicks):
    return TIPOS_REGIME[0], "Todas", "Todos", []


@callback(
    Output(f"{PREFIX}-medida-container", "children"),
    Input(f"{PREFIX}-tipo", "value"),
    Input(f"{PREFIX}-descricao", "value"),
    Input(f"{PREFIX}-codigo", "value"),
    Input(f"{PREFIX}-uf", "value"),
)
def _atualizar_medidas(tipo, codigo_descricao, codigo_escolhido, ufs_escolhidas):
    df, erro = _buscar_comparacao(tipo, codigo_descricao, codigo_escolhido, ufs_escolhidas)
    if erro:
        return info_box(erro)

    opcoes_medida = sorted(df["medida"].unique())
    medida_padrao = MEDIDA_PRINCIPAL.get(tipo)
    default_medida = [medida_padrao] if medida_padrao in opcoes_medida else opcoes_medida[:1]

    return html.Div([
        html.Label("Medidas"),
        dcc.Dropdown(
            id=f"{PREFIX}-medidas",
            options=[{"label": rotulo_medida(m), "value": m} for m in opcoes_medida],
            value=default_medida,
            multi=True,
        ),
        html.P(
            "Medidas com escalas muito diferentes ficam ilegíveis juntas no mesmo "
            "gráfico — por isso o padrão mostra só a medida principal. Adicione "
            "mais se quiser comparar.",
            className="caption",
        ),
    ])


@callback(
    Output(f"{PREFIX}-results", "children"),
    Input(f"{PREFIX}-tipo", "value"),
    Input(f"{PREFIX}-descricao", "value"),
    Input(f"{PREFIX}-codigo", "value"),
    Input(f"{PREFIX}-uf", "value"),
    Input(f"{PREFIX}-medida-container", "children"),
    Input(f"{PREFIX}-medidas", "value"),
)
def _renderizar_resultados(tipo, codigo_descricao, codigo_escolhido, ufs_escolhidas, _medida_container, medidas_escolhidas):
    df, erro = _buscar_comparacao(tipo, codigo_descricao, codigo_escolhido, ufs_escolhidas)
    if erro:
        return None

    if not medidas_escolhidas:
        return info_box("Escolha ao menos uma medida.")

    df = df[df["medida"].isin(medidas_escolhidas)].copy()

    ultimo_periodo = df["period_start"].max()
    df_periodo = df[df["period_start"] == ultimo_periodo].copy()

    uf_label = ufs_escolhidas[0] if len(ufs_escolhidas) == 1 else f"{df_periodo['state_name'].nunique()} UFs"

    media_medida = df_periodo.groupby("medida")[["valor_desonerado", "valor_nao_desonerado"]].mean().reset_index()
    media_medida["medida"] = media_medida["medida"].map(rotulo_medida)
    media_longa = media_medida.melt(
        id_vars="medida",
        value_vars=["valor_nao_desonerado", "valor_desonerado"],
        var_name="regime",
        value_name="valor_médio",
    )
    media_longa["regime"] = media_longa["regime"].map(
        {"valor_desonerado": "Desonerado", "valor_nao_desonerado": "Não Desonerado"}
    )
    media_longa["rótulo"] = media_longa["valor_médio"].apply(formatar_moeda_grafico)

    fig = px.bar(media_longa, x="medida", y="valor_médio", color="regime", barmode="group", text="rótulo")
    fig.update_traces(hovertemplate="%{x}<br>%{text}<extra></extra>")
    fig.update_layout(xaxis_title="Medida", yaxis_title="Valor médio (R$)", legend_title="Regime")

    def _formatar_diferenca(v: float) -> str:
        if pd.isna(v):
            return "-"
        return f"{v * 100:.1f}%".replace(".", ",")

    df_tabela = df_periodo[
        ["medida", "state_name", "valor_nao_desonerado", "valor_desonerado", "diferenca_percentual"]
    ].copy()
    df_tabela["medida"] = df_periodo["medida"].map(rotulo_medida)
    df_tabela["valor_nao_desonerado"] = df_periodo["valor_nao_desonerado"].apply(formatar_moeda_grafico)
    df_tabela["valor_desonerado"] = df_periodo["valor_desonerado"].apply(formatar_moeda_grafico)
    df_tabela["diferenca_percentual"] = df_periodo["diferenca_percentual"].apply(_formatar_diferenca)
    df_tabela = df_tabela.rename(
        columns={
            "medida": "Medida",
            "state_name": "UF",
            "valor_nao_desonerado": "Não Desonerado",
            "valor_desonerado": "Desonerado",
            "diferenca_percentual": "Diferença",
        }
    )

    return [
        html.H3(f"Comparação no período mais recente ({formatar_periodo(ultimo_periodo)}) — {uf_label}", className="section-subheader"),
        dcc.Graph(figure=fig),
        data_table(df_tabela),
    ]
