import dash
import plotly.express as px
from dash import Input, Output, callback, dcc, html

from components import data_table, filter_row, info_box, limpar_filtros_button, page_header
from gold import TIPO_LABELS, TIPOS, formatar_periodo, list_ufs, query, rotulo_sim_nao

# Desativada temporariamente pra focar o trabalho na página 1 — descomentar
# pra reativar.
# dash.register_page(__name__, path="/indice-de-reajuste", name="5. Índice de Reajuste", title="Índice de Reajuste", order=5)

PREFIX = "ir"


def layout(**kwargs):
    ufs = list_ufs()
    return html.Div(
        [
            *page_header(
                "Índice de Reajuste",
                "Base 100 no primeiro período observado de cada série. n_insumos é o "
                "tamanho da amostra por trás do índice — cuidado com períodos com "
                "amostra pequena.",
            ),
            limpar_filtros_button(f"{PREFIX}-limpar"),
            filter_row(
                ("Tipo", dcc.Dropdown(
                    id=f"{PREFIX}-tipo",
                    options=[{"label": TIPO_LABELS[t], "value": t} for t in TIPOS],
                    value=TIPOS[0],
                    clearable=False,
                )),
                ("UFs (vazio = todas)", dcc.Dropdown(
                    id=f"{PREFIX}-uf",
                    options=[{"label": n, "value": n} for n in ufs["state_name"]],
                    value=[],
                    multi=True,
                )),
            ),
            html.Div(id=f"{PREFIX}-results"),
        ]
    )


@callback(
    Output(f"{PREFIX}-tipo", "value"),
    Output(f"{PREFIX}-uf", "value"),
    Input(f"{PREFIX}-limpar", "n_clicks"),
    prevent_initial_call=True,
)
def _limpar_filtros(n_clicks):
    return TIPOS[0], []


@callback(
    Output(f"{PREFIX}-results", "children"),
    Input(f"{PREFIX}-tipo", "value"),
    Input(f"{PREFIX}-uf", "value"),
)
def _renderizar_resultados(tipo, ufs_escolhidas):
    ufs = list_ufs()
    sql = "select state_slug, desonerado, period_start, indice, n_insumos from vw_indice_reajuste where tipo = ?"
    params: list = [tipo]

    if ufs_escolhidas:
        slugs = ufs[ufs["state_name"].isin(ufs_escolhidas)]["state_slug"].tolist()
        placeholders = ",".join(["?"] * len(slugs))
        sql += f" and state_slug in ({placeholders})"
        params.extend(slugs)

    df = query(sql, params)

    if df.empty:
        return info_box("Sem dados.")

    df = df.merge(ufs[["state_slug", "state_name"]], on="state_slug", how="left")
    df["série"] = df["state_name"] + df["desonerado"].map({True: " (desonerado)", False: " (não desonerado)"})
    df["publicação"] = df["period_start"].apply(formatar_periodo)
    df["índice_rótulo"] = df["indice"].apply(lambda v: f"{v:.1f}".replace(".", ","))

    fig = px.line(
        df,
        x="period_start",
        y="indice",
        color="série",
        markers=True,
        custom_data=["publicação", "índice_rótulo"],
    )
    fig.update_traces(hovertemplate="Publicação: %{customdata[0]}<br>Índice: %{customdata[1]}<extra></extra>")
    fig.add_hline(y=100, line_dash="dot", annotation_text="base")
    fig.update_layout(xaxis_title="Período", yaxis_title="Índice (base 100)")

    df_tabela = df[["state_name", "desonerado", "period_start", "indice", "n_insumos"]].copy()
    df_tabela["desonerado"] = df["desonerado"].apply(rotulo_sim_nao)
    df_tabela["period_start"] = df["period_start"].apply(formatar_periodo)
    df_tabela["indice"] = df["indice"].round(1)
    df_tabela = df_tabela.rename(
        columns={
            "state_name": "UF",
            "desonerado": "Desonerado",
            "period_start": "Publicação",
            "indice": "Índice",
            "n_insumos": "Nº de Insumos",
        }
    )

    return [
        dcc.Graph(figure=fig),
        data_table(df_tabela),
    ]
