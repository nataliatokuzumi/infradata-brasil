import dash
import dash_mantine_components as dmc
import pandas as pd
import plotly.express as px
from dash import Input, Output, State, callback, ctx, dcc, no_update

from components import filter_row, info_box, metric_card, metric_row, page_header
from gold import (
    MEDIDA_PRINCIPAL,
    TIPO_LABELS,
    TIPOS,
    formatar_faixa_moeda,
    formatar_moeda,
    formatar_moeda_grafico,
    formatar_periodo,
    list_insumos,
    list_ufs,
    query,
    rotulo_medida,
)

# Página 1 unifica o que antes eram duas páginas (Preço por Item + Evolução
# de Preços) — mesmo conjunto de filtros no topo, seções empilhadas embaixo.
# As páginas 3-9 foram desativadas (register_page comentado) pra focar o
# trabalho nesta página por enquanto.
dash.register_page(
    __name__,
    path="/preco-por-item",
    name="Análise de Insumos",
    title="Análise de Insumos",
    order=1,
)

PREFIX = "pi"

REGIME_OPCOES = ["Ambos", "Não Desonerado", "Desonerado"]
COR_REGIME = {"Não Desonerado": "#228be6", "Desonerado": "#2b8a3e"}


def _formatar_variacao_pct(v) -> str:
    if v is None or pd.isna(v):
        return "—"
    return f"{v * 100:+.1f}%".replace(".", ",")


def _com_transparencia(cor: str, alpha: float) -> str:
    """Converte uma cor hex ("#rrggbb", como as do colorway do template
    Plotly) pra rgba com a opacidade dada — usado pro preenchimento
    translúcido do gráfico de evolução."""
    cor = cor.lstrip("#")
    if len(cor) == 6:
        r, g, b = int(cor[0:2], 16), int(cor[2:4], 16), int(cor[4:6], 16)
        return f"rgba({r}, {g}, {b}, {alpha})"
    return cor


def _buscar_preco_atual(tipo, codigo_descricao, codigo_escolhido, uf_escolhida, regime):
    sql = "select * from vw_preco_atual where tipo = ?"
    params: list = [tipo]

    if codigo_descricao != "Todas":
        sql += " and codigo = ?"
        params.append(codigo_descricao)

    if codigo_escolhido != "Todos":
        sql += " and codigo = ?"
        params.append(codigo_escolhido)

    if uf_escolhida != "Todas":
        sql += " and state_name = ?"
        params.append(uf_escolhida)

    if regime == "Não Desonerado":
        sql += " and not desonerado"
    elif regime == "Desonerado":
        sql += " and desonerado"

    sql += " order by descricao, state_name, medida"

    return query(sql, params)


def _buscar_serie_evolucao(tipo, codigo_descricao, codigo_escolhido, uf_escolhida, regime):
    if uf_escolhida != "Todas":
        sql = """
            select ve.tipo, ve.codigo, ve.descricao, ve.medida, ve.state_name, ve.desonerado,
                   ve.period_start, ve.valor, ve.variacao_percentual, di.unidade
            from vw_evolucao_preco ve
            join dim_insumo di on di.tipo = ve.tipo and di.codigo = ve.codigo
            where ve.tipo = ? and ve.state_name = ?
        """
        params: list = [tipo, uf_escolhida]

        if codigo_descricao != "Todas":
            sql += " and ve.codigo = ?"
            params.append(codigo_descricao)

        if codigo_escolhido != "Todos":
            sql += " and ve.codigo = ?"
            params.append(codigo_escolhido)

        if regime == "Não Desonerado":
            sql += " and not ve.desonerado"
        elif regime == "Desonerado":
            sql += " and ve.desonerado"

        sql += " order by ve.medida, ve.desonerado, ve.period_start"

        df = query(sql, params)
    else:
        # Sem UF selecionada não dá pra plotar uma série por UF (viraria
        # dezenas de linhas empilhadas) — mostra a média entre as UFs por
        # período em vez de bloquear o gráfico. variacao_percentual não vem
        # da view aqui (ela é calculada por UF) — é recalculada em cima da
        # própria série já agregada, com pct_change por medida/regime.
        sql = """
            select ve.tipo, ve.codigo, ve.descricao, ve.medida, ve.desonerado,
                   ve.period_start, avg(ve.valor) as valor, di.unidade
            from vw_evolucao_preco ve
            join dim_insumo di on di.tipo = ve.tipo and di.codigo = ve.codigo
            where ve.tipo = ?
        """
        params = [tipo]

        if codigo_descricao != "Todas":
            sql += " and ve.codigo = ?"
            params.append(codigo_descricao)

        if codigo_escolhido != "Todos":
            sql += " and ve.codigo = ?"
            params.append(codigo_escolhido)

        if regime == "Não Desonerado":
            sql += " and not ve.desonerado"
        elif regime == "Desonerado":
            sql += " and ve.desonerado"

        sql += """
            group by ve.tipo, ve.codigo, ve.descricao, ve.medida, ve.desonerado, di.unidade, ve.period_start
            order by ve.medida, ve.desonerado, ve.period_start
        """

        df = query(sql, params)
        if not df.empty:
            df["state_name"] = "Todas as UFs"
            df["variacao_percentual"] = df.groupby(["medida", "desonerado"])["valor"].pct_change()

    if df.empty:
        return df, "Sem dados pra essa combinação de filtros."

    # um gráfico de evolução só faz sentido pra um item — com os filtros
    # nesse estado ainda sobra mais de um código, então pede pra escolher
    # Descrição/Código antes de desenhar.
    if df["codigo"].nunique() > 1:
        return df.iloc[0:0], "Escolha uma Descrição (ou Código) específica pra ver a evolução de preço."

    return df, None


def layout(**kwargs):
    ufs = list_ufs()
    return dmc.Stack(
        [
            *page_header(
                "Análise de Insumos",
                "Descubra o preço mais recente e a série histórica do insumo por UF e regime tributário. "
                "Pesquise pelo insumo utilizando os filtros abaixo.",
            ),
            filter_row(
                ("", dmc.Select(
                    id=f"{PREFIX}-tipo",
                    label="Tipo",
                    data=[{"label": TIPO_LABELS[t], "value": t} for t in TIPOS],
                    value=TIPOS[0],
                    allowDeselect=False,
                )),
                # data já vem com o item "Todas"/"Todos" desde o layout
                # inicial (não vazio) — sem isso, o Select nasce com value
                # apontando pra uma opção que ainda não existe (data só é
                # preenchido depois, por _atualizar_opcoes_insumo), e ele
                # zera o value pra None nesse instante. Esse None então virava
                # um parâmetro NULL no SQL (`codigo = ?` com None), que nunca
                # bate com nada — daí a página abrir direto em "sem dados",
                # só resolvendo depois de clicar em "Limpar filtros".
                ("", dmc.Select(
                    id=f"{PREFIX}-descricao",
                    label="Descrição",
                    data=[{"label": "Todas", "value": "Todas"}],
                    value="Todas",
                    searchable=True,
                    allowDeselect=False,
                )),
                ("", dmc.Select(
                    id=f"{PREFIX}-codigo",
                    label="Código",
                    data=[{"label": "Todos", "value": "Todos"}],
                    value="Todos",
                    searchable=True,
                    allowDeselect=False,
                )),
                ("", dmc.Select(
                    id=f"{PREFIX}-uf",
                    label="UF",
                    data=[{"label": "Todas", "value": "Todas"}]
                    + [{"label": n, "value": n} for n in ufs["state_name"]],
                    value="Todas",
                    searchable=True,
                    allowDeselect=False,
                )),
                # Materiais não tem variante desonerado — o filtro continua
                # visível (não some da página), só fica desabilitado e sem
                # opções/valor pra escolher.
                ("", dmc.Select(
                    id=f"{PREFIX}-regime",
                    label="Regime",
                    data=[{"label": o, "value": o} for o in REGIME_OPCOES],
                    value="Ambos",
                    allowDeselect=False,
                )),
                # filter_row usa align="flex-end", que alinha esse
                # botão pela base com os inputs dos outros filtros da
                # fileira (que têm um label de verdade acima).
                ("", dmc.Button("Limpar filtros", id=f"{PREFIX}-limpar", n_clicks=0, variant="light")),
            ),
            # KPIs em destaque no topo (fora de qualquer card, como métrica
            # principal da página) — só aparece quando os filtros já
            # apontam pra um único item.
            dmc.Box(id=f"{PREFIX}-kpi-results"),
            dmc.Paper(
                [
                    dmc.Title("Evolução de Preços", order=3, mb="xs"),
                    dmc.Text(
                        "Série histórica do item/UF selecionados acima, com variação vs. o período anterior.",
                        c="dimmed",
                        size="sm",
                        mb="sm",
                    ),
                    dmc.Box(id=f"{PREFIX}-medida-container"),
                    dmc.Box(id=f"{PREFIX}-evolucao-results"),
                ],
                withBorder=True,
                radius="md",
                p="md",
            ),
            dmc.Paper(
                [
                    dmc.Title("Preço Atual por Estado", order=3, mb="sm"),
                    dmc.Box(id=f"{PREFIX}-preco-atual-results"),
                ],
                withBorder=True,
                radius="md",
                p="md",
            ),
        ],
        gap="md",
    )


@callback(
    Output(f"{PREFIX}-descricao", "data"),
    Output(f"{PREFIX}-codigo", "data"),
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
    Output(f"{PREFIX}-descricao", "value"),
    Output(f"{PREFIX}-codigo", "value"),
    Input(f"{PREFIX}-descricao", "value"),
    Input(f"{PREFIX}-codigo", "value"),
    prevent_initial_call=True,
)
def _sincronizar_descricao_codigo(descricao_valor, codigo_valor):
    # Descrição e Código eram dois filtros AND independentes que, na
    # prática, sempre apontam pro mesmo insumo (o value de Descrição já É o
    # codigo, só o label mostra a descrição) — agora escolher um define o
    # outro, em vez de precisar preencher os dois ou eles brigarem se
    # apontarem pra códigos diferentes. Só escreve no campo que NÃO disparou
    # o callback, senão os dois ficariam se retriggerando um ao outro.
    gatilho = ctx.triggered_id
    if gatilho == f"{PREFIX}-descricao":
        novo_codigo = descricao_valor if descricao_valor != "Todas" else "Todos"
        if novo_codigo == codigo_valor:
            return no_update, no_update
        return no_update, novo_codigo
    if gatilho == f"{PREFIX}-codigo":
        nova_descricao = codigo_valor if codigo_valor != "Todos" else "Todas"
        if nova_descricao == descricao_valor:
            return no_update, no_update
        return nova_descricao, no_update
    return no_update, no_update


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
    return valor_atual or "Ambos", [{"label": o, "value": o} for o in REGIME_OPCOES], False


@callback(
    Output(f"{PREFIX}-tipo", "value"),
    Output(f"{PREFIX}-descricao", "value"),
    Output(f"{PREFIX}-codigo", "value"),
    Output(f"{PREFIX}-uf", "value"),
    Input(f"{PREFIX}-limpar", "n_clicks"),
    prevent_initial_call=True,
)
def _limpar_filtros(n_clicks):
    return TIPOS[0], "Todas", "Todos", "Todas"


# --------------------------------------------------------------- Preço Atual

@callback(
    Output(f"{PREFIX}-kpi-results", "children"),
    Input(f"{PREFIX}-tipo", "value"),
    Input(f"{PREFIX}-descricao", "value"),
    Input(f"{PREFIX}-codigo", "value"),
    Input(f"{PREFIX}-uf", "value"),
    Input(f"{PREFIX}-regime", "value"),
)
def _renderizar_kpis(tipo, codigo_descricao, codigo_escolhido, uf_escolhida, regime):
    # Sempre busca com uf="Todas", mesmo que o filtro de UF esteja setado —
    # Preço Médio/Menor/Maior precisam continuar refletindo TODAS as UFs
    # independente da UF escolhida no filtro (senão, com uma UF específica
    # selecionada, esses 3 cards colapsavam pra aquela UF só: média de 1
    # linha = ela mesma, mínimo = máximo = ela mesma). A UF escolhida é
    # aplicada depois, em Python, só nos cards que são explicitamente "na UF
    # selecionada".
    df = _buscar_preco_atual(tipo, codigo_descricao, codigo_escolhido, "Todas", regime)

    # Os KPIs só fazem sentido quando os filtros já apontam pra um único
    # item (código) — com mais de um item misturado, "preço médio"/"menor
    # preço" etc. deixariam de ter uma leitura única.
    if df.empty or df["codigo"].nunique() > 1:
        return None

    item = df.iloc[0]
    principal = MEDIDA_PRINCIPAL[tipo]
    df_principal = df[df["medida"] == principal]
    # equipamentos não tem unidade publicada pelo SICRO (fica None) — nesse
    # caso o sufixo simplesmente não aparece, em vez de mostrar "/ None".
    sufixo_unidade = f" / {item['unidade']}" if item["unidade"] else ""

    # "código | descrição", só o código em negrito — dois spans dentro do
    # mesmo Text em vez de um valor só, pra ter pesos diferentes na mesma
    # linha (metric_card não reembrulha quando value já é um componente).
    bloco_insumo = dmc.Stack(
        [
            metric_card(
                "Insumo",
                dmc.Text([
                    dmc.Text(item["codigo"], span=True, fw=700, size="md"),
                    " | ",
                    dmc.Text(item["descricao"], span=True, fw=400, size="md"),
                ]),
            ),
            # px="md" pra alinhar com o conteúdo interno do card Insumo
            # acima (que tem padding p="md") — sem isso o texto começava
            # mais à esquerda que o card, parecendo desalinhado.
            dmc.Text(
                f"Publicação mais recente: {formatar_periodo((df_principal if not df_principal.empty else df)['period_start'].max())}",
                size="sm",
                c="dimmed",
                px="md",
            ),
        ],
        gap="xs",
    )

    if df_principal.empty:
        return [
            info_box(
                f"Sem valor pra medida principal ({rotulo_medida(principal)}) com os filtros atuais "
                "— veja a tabela abaixo pras medidas disponíveis."
            ),
            bloco_insumo,
        ]

    # Preço atual e variação na UF selecionada só têm uma leitura única
    # quando UMA UF está escolhida — com "Todas", não há uma UF de
    # referência pra mostrar esses dois blocos.
    if uf_escolhida != "Todas":
        sub_uf = df_principal[df_principal["state_name"] == uf_escolhida]
        if len(sub_uf) == 1 or (len(sub_uf) > 1 and sub_uf["valor"].nunique() == 1):
            preco_atual_uf = formatar_moeda(sub_uf.iloc[0]["valor"]) + sufixo_unidade
        elif len(sub_uf) > 1:
            # mais de uma linha pra mesma UF acontece com regime="Ambos" e o
            # item publicado nos dois regimes ao mesmo tempo, com preços
            # diferentes entre eles.
            preco_atual_uf = formatar_faixa_moeda(sub_uf["valor"].min(), sub_uf["valor"].max()) + sufixo_unidade
        else:
            preco_atual_uf = "—"

        df_evolucao, erro_evolucao = _buscar_serie_evolucao(tipo, codigo_descricao, codigo_escolhido, uf_escolhida, regime)
        variacao_fmt = "—"
        if not erro_evolucao:
            serie_principal = df_evolucao[df_evolucao["medida"] == principal].sort_values("period_start")
            if not serie_principal.empty:
                variacao_fmt = _formatar_variacao_pct(serie_principal.iloc[-1]["variacao_percentual"])

        delta_uf = uf_escolhida
    else:
        preco_atual_uf = "—"
        variacao_fmt = "—"
        delta_uf = "Selecione uma UF"

    linha_min = df_principal.loc[df_principal["valor"].idxmin()]
    linha_max = df_principal.loc[df_principal["valor"].idxmax()]

    linha2 = metric_row(
        metric_card("Preço Atual", preco_atual_uf, delta_uf),
        metric_card("Variação", variacao_fmt, delta_uf),
        metric_card("Preço Médio", formatar_moeda(df_principal["valor"].mean()) + sufixo_unidade),
        metric_card("Menor Preço", formatar_moeda(linha_min["valor"]) + sufixo_unidade, linha_min["state_name"]),
        metric_card("Maior Preço", formatar_moeda(linha_max["valor"]) + sufixo_unidade, linha_max["state_name"]),
        cols={"base": 1, "sm": 2, "md": 3, "lg": 5},
    )

    return [linha2, bloco_insumo]


@callback(
    Output(f"{PREFIX}-preco-atual-results", "children"),
    Input(f"{PREFIX}-tipo", "value"),
    Input(f"{PREFIX}-descricao", "value"),
    Input(f"{PREFIX}-codigo", "value"),
    Input(f"{PREFIX}-regime", "value"),
)
def _renderizar_grafico_preco_atual(tipo, codigo_descricao, codigo_escolhido, regime):
    # Sempre "Todas" as UFs — é um gráfico comparando estados entre si, não
    # faz sentido restringir a uma UF só (mesmo padrão dos cards Preço
    # Médio/Menor/Maior: ver _renderizar_kpis). Por isso não depende do
    # filtro de UF.
    df = _buscar_preco_atual(tipo, codigo_descricao, codigo_escolhido, "Todas", regime)

    if df.empty:
        return info_box("Sem dados pra essa combinação de filtros.")

    if df["codigo"].nunique() > 1:
        return info_box("Escolha uma Descrição (ou Código) específica pra ver o preço por estado.")

    principal = MEDIDA_PRINCIPAL[tipo]
    df_principal = df[df["medida"] == principal].copy()

    if df_principal.empty:
        return info_box(f"Sem valor pra medida principal ({rotulo_medida(principal)}) com os filtros atuais.")

    unidade = df_principal["unidade"].iloc[0]
    sufixo_unidade = f" / {unidade}" if unidade else ""

    df_principal["regime"] = df_principal["desonerado"].map({True: "Desonerado", False: "Não Desonerado"})
    df_principal["valor_rótulo"] = df_principal["valor"].apply(formatar_moeda_grafico)
    estados_ordenados = sorted(df_principal["state_name"].unique())

    fig = px.bar(
        df_principal,
        x="state_name",
        y="valor",
        color="regime",
        barmode="group",
        text="valor_rótulo",
        category_orders={"state_name": estados_ordenados},
        color_discrete_map=COR_REGIME,
        custom_data=["state_name", "valor_rótulo"],
    )
    fig.update_traces(
        textposition="outside",
        textangle=-90,
        hovertemplate=f"%{{customdata[0]}}<br>Valor: %{{customdata[1]}}{sufixo_unidade}<extra></extra>",
    )
    fig.update_layout(
        xaxis_title=None,
        yaxis_title="Valor (R$)",
        xaxis=dict(showgrid=False),
        # rótulo vertical (textangle=-90) precisa de mais espaço acima das
        # barras do que o padrão dá — sem isso ele cortava no topo do
        # gráfico.
        yaxis=dict(showgrid=True, gridcolor="rgba(0, 0, 0, 0.06)", zeroline=False, rangemode="tozero"),
        legend_title="Regime",
        height=520,
        margin=dict(t=80),
        plot_bgcolor="rgba(0, 0, 0, 0)",
        paper_bgcolor="rgba(0, 0, 0, 0)",
    )

    return dcc.Graph(figure=fig)


# ---------------------------------------------------------- Evolução de Preços

@callback(
    Output(f"{PREFIX}-medida-container", "children"),
    Input(f"{PREFIX}-tipo", "value"),
    Input(f"{PREFIX}-descricao", "value"),
    Input(f"{PREFIX}-codigo", "value"),
    Input(f"{PREFIX}-uf", "value"),
    Input(f"{PREFIX}-regime", "value"),
)
def _atualizar_medidas(tipo, codigo_descricao, codigo_escolhido, uf_escolhida, regime):
    df, erro = _buscar_serie_evolucao(tipo, codigo_descricao, codigo_escolhido, uf_escolhida, regime)
    if erro:
        return info_box(erro)

    # Medidas do mesmo item têm escalas muito diferentes entre si (ex:
    # valor_aquisicao de equipamento fica na casa dos milhares,
    # custo_produtivo do mesmo item fica nas dezenas) — plotadas juntas sem
    # filtro, as menores ficam achatadas em zero e o gráfico vira ruído. Por
    # isso o padrão mostra só a medida principal do tipo; dá pra adicionar
    # mais pra comparar.
    opcoes_medida = sorted(df["medida"].unique())
    medida_padrao = MEDIDA_PRINCIPAL.get(tipo)
    default_medida = [medida_padrao] if medida_padrao in opcoes_medida else opcoes_medida[:1]

    return dmc.MultiSelect(
        id=f"{PREFIX}-medidas",
        label="Medidas",
        data=[{"label": rotulo_medida(m), "value": m} for m in opcoes_medida],
        value=default_medida,
    )


@callback(
    Output(f"{PREFIX}-evolucao-results", "children"),
    Input(f"{PREFIX}-tipo", "value"),
    Input(f"{PREFIX}-descricao", "value"),
    Input(f"{PREFIX}-codigo", "value"),
    Input(f"{PREFIX}-uf", "value"),
    Input(f"{PREFIX}-regime", "value"),
    Input(f"{PREFIX}-medida-container", "children"),
    Input(f"{PREFIX}-medidas", "value"),
)
def _renderizar_evolucao(tipo, codigo_descricao, codigo_escolhido, uf_escolhida, regime, _medida_container, medidas_escolhidas):
    df, erro = _buscar_serie_evolucao(tipo, codigo_descricao, codigo_escolhido, uf_escolhida, regime)
    if erro:
        return None

    if not medidas_escolhidas:
        return info_box("Escolha ao menos uma medida.")

    unidade = df["unidade"].iloc[0]
    sufixo_unidade = f" / {unidade}" if unidade else ""

    df = df[df["medida"].isin(medidas_escolhidas)].copy()

    df["medida"] = df["medida"].map(rotulo_medida)
    df["série"] = df["medida"] + df["desonerado"].map({True: " (desonerado)", False: " (não desonerado)"})
    df["valor_rótulo"] = df["valor"].apply(formatar_moeda_grafico)
    df["publicação"] = df["period_start"].apply(formatar_periodo)

    # mesma cor por regime do gráfico de barras (COR_REGIME) — sem isso, a
    # paleta padrão do template escolhia as cores por conta própria e o
    # "desonerado" acabava caindo em vermelho aqui também.
    cor_por_serie = {
        serie: COR_REGIME["Desonerado" if desonerado else "Não Desonerado"]
        for serie, desonerado in df[["série", "desonerado"]].drop_duplicates().itertuples(index=False)
    }

    fig = px.line(
        df,
        x="period_start",
        y="valor",
        color="série",
        markers=True,
        line_shape="spline",
        color_discrete_map=cor_por_serie,
        custom_data=["publicação", "valor_rótulo"],
    )
    # Curva suave (spline) + preenchimento translúcido embaixo da linha +
    # marcadores discretos, sem rótulo de valor fixo em cada ponto (esse
    # continua disponível no hover) — visual de "gráfico de crescimento",
    # não de planilha com número em cima de cada ponto.
    for trace in fig.data:
        cor = trace.line.color
        trace.line.width = 3
        trace.marker.size = 6
        trace.fill = "tozeroy"
        trace.fillcolor = _com_transparencia(cor, 0.12)
    fig.update_traces(
        hovertemplate=f"Publicação: %{{customdata[0]}}<br>Valor: %{{customdata[1]}}{sufixo_unidade}<extra></extra>",
    )
    # fill="tozeroy" preenche até y=0 na geometria — com preços numa faixa
    # estreita (ex: 100 a 110), isso deixava a área pintada tomando quase a
    # altura inteira do gráfico e achatando a variação real lá em cima.
    # Travar o range do eixo Y perto do mínimo/máximo dos dados (em vez de
    # deixar o autorange incluir o zero) resolve sem precisar tirar o
    # preenchimento.
    y_min, y_max = df["valor"].min(), df["valor"].max()
    folga = (y_max - y_min) * 0.15 if y_max > y_min else max(y_max * 0.1, 1)

    fig.update_layout(
        xaxis_title="Período",
        yaxis_title="Valor (R$)",
        xaxis=dict(showgrid=False),
        yaxis=dict(
            showgrid=True,
            gridcolor="rgba(0, 0, 0, 0.06)",
            zeroline=False,
            range=[y_min - folga, y_max + folga],
        ),
        hovermode="x unified",
        plot_bgcolor="rgba(0, 0, 0, 0)",
        paper_bgcolor="rgba(0, 0, 0, 0)",
    )

    if uf_escolhida == "Todas":
        # o nº de UFs com dado disponível pode variar de período pra
        # período (nem toda UF publica todo trimestre) — por isso a nota
        # não cita um número fixo de UFs.
        return [
            dmc.Text("Média entre as UFs com dado disponível em cada período.", c="dimmed", size="sm", mb="xs"),
            dcc.Graph(figure=fig),
        ]

    return dcc.Graph(figure=fig)
