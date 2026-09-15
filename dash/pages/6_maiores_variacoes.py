import dash
import dash_mantine_components as dmc
import pandas as pd
import plotly.express as px
from dash import Input, Output, State, callback, dcc

from components import data_table, filter_row, info_box, page_header
from gold import MEDIDA_PRINCIPAL, TIPO_LABELS, TIPOS, formatar_moeda_grafico, formatar_periodo, list_ufs, query, rotulo_medida, rotulo_regiao

dash.register_page(
    __name__,
    path="/maiores-variacoes",
    name="Maiores Variações",
    title="Maiores Variações",
    order=6,
)

PREFIX = "mv"

# Sem "Ambos" aqui de propósito: diferente de Análise de Insumos, misturar
# os dois regimes no mesmo ranking fazia cada item aparecer até 2x (mais os
# vários componentes de custo somados — ver _buscar_maiores_variacoes).
REGIME_OPCOES = ["Não Desonerado", "Desonerado"]


def _buscar_maiores_variacoes(tipo, uf_escolhida, regiao, regime):
    ufs = list_ufs()

    if uf_escolhida != "Todos":
        slug_rows = ufs[ufs["state_name"] == uf_escolhida]["state_slug"]
        if slug_rows.empty:
            return pd.DataFrame()
        slugs = slug_rows
    else:
        # UF="Todos": ranqueia junto todas as UFs da região escolhida (ou
        # do Brasil inteiro, se a região também for "Todas") em vez de UF
        # por UF.
        slugs = ufs["state_slug"] if regiao == "Todas" else ufs[ufs["region"] == regiao]["state_slug"]

    if slugs.empty:
        return pd.DataFrame()

    # vw_maiores_variacoes ranqueia por (insumo, UF, regime, MEDIDA) — pra
    # equipamentos/mão de obra, que têm várias medidas (componentes de
    # custo) e 2 regimes, isso inundava o Top 20 com o mesmo insumo
    # repetido várias vezes (confirmado: um único item ocupou 12 das 20
    # posições num teste). Por isso não usa a view pronta — refaz a mesma
    # lógica dela (último período disponível de cada UF, ranqueado por
    # |variação%|) direto em cima de vw_evolucao_preco, já restrita à
    # medida principal do tipo e a um regime por vez.
    principal = MEDIDA_PRINCIPAL[tipo]
    placeholders = ",".join(["?"] * len(slugs))
    sql = f"""
        with evolucao as (
            select *
            from vw_evolucao_preco
            where tipo = ? and medida = ? and variacao_percentual is not null
              and state_slug in ({placeholders})
    """
    params: list = [tipo, principal, *slugs.tolist()]

    if regime == "Não Desonerado":
        sql += " and not desonerado"
    elif regime == "Desonerado":
        sql += " and desonerado"
    # materiais não tem variante desonerado — regime vem None (filtro
    # desabilitado) e nenhuma das duas condições acima entra, o que já é
    # o comportamento certo (materiais só tem uma linha por UF/período).

    sql += """
        ),
        ultimo_periodo as (
            select state_slug, max(period_start) as ultimo_period_start
            from evolucao
            group by 1
        ),
        apenas_ultimo as (
            select evolucao.*
            from evolucao
            inner join ultimo_periodo
                on  evolucao.state_slug   = ultimo_periodo.state_slug
                and evolucao.period_start = ultimo_periodo.ultimo_period_start
        )
        select
            codigo, descricao, medida, state_name, period_start, valor, valor_anterior, variacao_percentual,
            row_number() over (order by abs(variacao_percentual) desc) as posicao
        from apenas_ultimo
        order by posicao
        limit 20
    """
    return query(sql, params)


def layout(**kwargs):
    ufs = list_ufs()
    return dmc.Stack(
        [
            *page_header(
                "Maiores Variações Recentes",
                "Top 20 itens com maior variação de preço (medida principal do tipo) no "
                "último período disponível da UF ou da região — sinal de risco pra linhas "
                "de orçamento.",
            ),
            filter_row(
                ("", dmc.Select(
                    id=f"{PREFIX}-tipo",
                    label="Tipo",
                    data=[{"label": TIPO_LABELS[t], "value": t} for t in TIPOS],
                    value=TIPOS[0],
                    allowDeselect=False,
                )),
                ("", dmc.Select(
                    id=f"{PREFIX}-regiao",
                    label="Região",
                    data=[{"label": "Todas", "value": "Todas"}]
                    + [{"label": rotulo_regiao(r), "value": r} for r in sorted(ufs["region"].unique())],
                    value="Todas",
                    allowDeselect=False,
                )),
                ("", dmc.Select(
                    id=f"{PREFIX}-uf",
                    label="UF",
                    data=[{"label": "Todos", "value": "Todos"}]
                    + [{"label": n, "value": n} for n in ufs["state_name"]],
                    value="Todos",
                    searchable=True,
                    allowDeselect=False,
                )),
                # Materiais não tem variante desonerado — o filtro continua
                # visível, só fica desabilitado e sem opções (mesmo padrão
                # da página Análise de Insumos).
                ("", dmc.Select(
                    id=f"{PREFIX}-regime",
                    label="Regime",
                    data=[{"label": o, "value": o} for o in REGIME_OPCOES],
                    value=REGIME_OPCOES[0],
                    allowDeselect=False,
                )),
                # filter_row usa align="flex-end", que alinha esse
                # botão pela base com os inputs dos outros filtros.
                ("", dmc.Button("Limpar filtros", id=f"{PREFIX}-limpar", n_clicks=0, variant="light")),
            ),
            dmc.Paper(
                [
                    dmc.Title("Maiores Variações", order=3, mb="sm"),
                    dmc.Box(id=f"{PREFIX}-grafico-results"),
                ],
                withBorder=True,
                radius="md",
                p="md",
            ),
            dmc.Paper(
                [
                    dmc.Title("Detalhamento", order=3, mb="sm"),
                    dmc.Box(id=f"{PREFIX}-tabela-results"),
                ],
                withBorder=True,
                radius="md",
                p="md",
            ),
        ],
        gap="md",
    )


@callback(
    Output(f"{PREFIX}-uf", "data"),
    Output(f"{PREFIX}-uf", "value", allow_duplicate=True),
    Input(f"{PREFIX}-regiao", "value"),
    State(f"{PREFIX}-uf", "value"),
    prevent_initial_call=True,
)
def _atualizar_opcoes_uf(regiao, uf_atual):
    ufs = list_ufs()
    if regiao != "Todas":
        ufs = ufs[ufs["region"] == regiao]

    opcoes = [{"label": "Todos", "value": "Todos"}] + [{"label": n, "value": n} for n in ufs["state_name"]]
    # "Todos" sempre continua válido (o gráfico passa a agregar pela
    # região nesse caso) — só troca o value se a UF específica atual não
    # pertence mais à região escolhida. Nunca deixa o value apontar pra
    # uma opção que não existe mais (isso já causou bug de "sem dados"
    # antes, ver página de Preço por Item).
    if uf_atual == "Todos" or uf_atual in ufs["state_name"].values:
        novo_valor = uf_atual
    else:
        novo_valor = ufs["state_name"].iloc[0] if not ufs.empty else "Todos"

    return opcoes, novo_valor


@callback(
    Output(f"{PREFIX}-regime", "value"),
    Output(f"{PREFIX}-regime", "data"),
    Output(f"{PREFIX}-regime", "disabled"),
    Input(f"{PREFIX}-tipo", "value"),
    State(f"{PREFIX}-regime", "value"),
)
def _alternar_regime(tipo, valor_atual):
    if tipo == "materiais":
        return None, [], True
    return valor_atual or REGIME_OPCOES[0], [{"label": o, "value": o} for o in REGIME_OPCOES], False


@callback(
    Output(f"{PREFIX}-tipo", "value"),
    Output(f"{PREFIX}-regiao", "value"),
    Output(f"{PREFIX}-uf", "value", allow_duplicate=True),
    Input(f"{PREFIX}-limpar", "n_clicks"),
    prevent_initial_call=True,
)
def _limpar_filtros(n_clicks):
    return TIPOS[0], "Todas", "Todos"


@callback(
    Output(f"{PREFIX}-grafico-results", "children"),
    Input(f"{PREFIX}-tipo", "value"),
    Input(f"{PREFIX}-uf", "value"),
    Input(f"{PREFIX}-regiao", "value"),
    Input(f"{PREFIX}-regime", "value"),
)
def _renderizar_grafico(tipo, uf_escolhida, regiao, regime):
    if not uf_escolhida:
        return info_box("Sem dados pra essa combinação.")

    df = _buscar_maiores_variacoes(tipo, uf_escolhida, regiao, regime)

    if df.empty:
        return info_box("Sem dados pra essa combinação.")

    df["variação%"] = (df["variacao_percentual"] * 100).round(1)
    df["variação%_rótulo"] = df["variação%"].apply(lambda v: f"{v:+.1f}%".replace(".", ","))
    df["medida"] = df["medida"].map(rotulo_medida)
    df["item"] = df["descricao"] + " — " + df["medida"]
    if uf_escolhida == "Todos":
        # sem UF fixa no filtro, o item sozinho não diz de onde é —
        # acrescenta a UF no rótulo pra não misturar tudo.
        df["item"] = df["item"] + " (" + df["state_name"] + ")"

    fig = px.bar(
        df.sort_values("variação%"),
        x="variação%",
        y="item",
        orientation="h",
        color="variação%",
        color_continuous_scale="RdYlGn",
        # sem isso, a escala de cor ancora no mínimo/máximo do que está
        # sendo exibido — se o Top 20 filtrado vier todo positivo (só
        # aumentos), o aumento MENOR (mas ainda positivo) virava vermelho
        # só por ser "o menor da lista". Fixar o centro em 0 garante que
        # vermelho/verde sempre reflitam queda/alta de verdade, não a
        # faixa local do filtro atual.
        color_continuous_midpoint=0,
        text="variação%_rótulo",
    )
    fig.update_traces(hovertemplate="%{y}<br>%{text}<extra></extra>")
    fig.update_layout(
        height=700,
        xaxis_title="Variação (%)",
        yaxis_title="",
        xaxis=dict(showgrid=True, gridcolor="rgba(0, 0, 0, 0.06)", zeroline=False),
        # side="right": nome do insumo do lado direito do gráfico, não
        # embaixo do eixo de variação (%) à esquerda.
        yaxis=dict(showgrid=False, side="right"),
        # a barra de cor (colorbar) por padrão nasce colada no lado
        # direito do gráfico — bem em cima dos nomes dos insumos que
        # também estão à direita agora. Horizontal, no topo, evita a
        # sobreposição de vez.
        coloraxis_colorbar=dict(
            title="Variação (%)",
            orientation="h",
            x=0.5,
            xanchor="center",
            y=1.08,
            yanchor="bottom",
            len=0.6,
            thickness=12,
        ),
        margin=dict(t=70),
        plot_bgcolor="rgba(0, 0, 0, 0)",
        paper_bgcolor="rgba(0, 0, 0, 0)",
    )

    return dcc.Graph(figure=fig)


@callback(
    Output(f"{PREFIX}-tabela-results", "children"),
    Input(f"{PREFIX}-tipo", "value"),
    Input(f"{PREFIX}-uf", "value"),
    Input(f"{PREFIX}-regiao", "value"),
    Input(f"{PREFIX}-regime", "value"),
)
def _renderizar_tabela(tipo, uf_escolhida, regiao, regime):
    if not uf_escolhida:
        return info_box("Sem dados pra essa combinação.")

    df = _buscar_maiores_variacoes(tipo, uf_escolhida, regiao, regime)

    if df.empty:
        return info_box("Sem dados pra essa combinação.")

    df["medida"] = df["medida"].map(rotulo_medida)
    df["variação%_rótulo"] = (df["variacao_percentual"] * 100).apply(lambda v: f"{v:+.1f}%".replace(".", ","))

    df_tabela = df[["codigo", "descricao", "medida", "state_name", "period_start", "valor_anterior", "valor", "variação%_rótulo"]].copy()
    df_tabela["period_start"] = df["period_start"].apply(formatar_periodo)
    df_tabela["valor_anterior"] = df["valor_anterior"].apply(formatar_moeda_grafico)
    df_tabela["valor"] = df["valor"].apply(formatar_moeda_grafico)
    df_tabela = df_tabela.rename(
        columns={
            "codigo": "Código",
            "descricao": "Descrição",
            "medida": "Medida",
            "state_name": "UF",
            "period_start": "Publicação",
            "valor_anterior": "Valor Anterior",
            "valor": "Valor Atual",
            "variação%_rótulo": "Variação",
        }
    )

    return data_table(df_tabela, filterable=False)
