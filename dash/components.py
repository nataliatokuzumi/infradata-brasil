"""Componentes reutilizados nas páginas, construídos em cima do Dash
Mantine Components pra bater com o visual do exemplo de referência
(financial-dashboard-example.plotly.app) — cartões (Paper), grid responsivo,
tipografia e tema claro/escuro vêm todos do Mantine. dash_table.DataTable
continua sendo usado pra tabela (sort/filtro/estilo condicional nativos que
o dmc.Table não tem), só que agora themado com as variáveis CSS do próprio
Mantine em vez de tokens nossos, pra acompanhar o toggle de tema sem
duplicar lógica."""
import dash_mantine_components as dmc
from dash import dash_table, html

# Paleta da marca Infradata Brasil (mesmas cores do logotipo em
# dash/assets/logo-mark*.svg) — ponto único pra qualquer gráfico ou
# componente que precise de uma cor "de marca" em vez de uma cor semântica
# de dado (ex: a escala RdYlGn de alta/queda em Maiores Variações continua
# semântica de propósito, não usa essa paleta).
BRAND = {
    "tinta": "#17253F",  # nanquim — estrutura do logo, texto de marca
    "ferrugem": "#AD5A1E",  # accent — cor primária do tema Mantine
    "cianotipo": "#0E2A45",  # navy do rodapé/fundo blueprint
    "papel": "#F4EFE4",  # papel de prancheta
    "linha_clara": "#EAF3FA",  # traços do logo sobre fundo escuro
    "barra_ambar": "#E6A94F",  # barras do logo sobre fundo escuro
}


def page_header(titulo: str, caption: str | list) -> list:
    return [
        dmc.Title(titulo, order=2),
        dmc.Text(caption, c="dimmed", size="sm", mb="md"),
    ]


def limpar_filtros_button(component_id: str):
    return dmc.Button("Limpar filtros", id=component_id, n_clicks=0, variant="light", size="sm", mb="md")


def filter_row(*campos) -> dmc.Grid:
    """Cada campo é (label, componente) — vira uma coluna numa grid
    responsiva, equivalente a st.columns(n). label vazio pula o <label> do
    helper (usado quando o próprio componente Mantine já renderiza seu
    rótulo interno via prop `label=`, ex: dmc.Select). align="flex-end"
    alinha todas as colunas pela base — é o que faz um botão sem label
    (ex: "Limpar filtros") ficar na mesma altura da caixa de input dos
    outros filtros, que têm um label de verdade acima."""
    return dmc.Grid(
        [
            dmc.GridCol(
                [html.Label(label), campo] if label else campo,
                span={"base": 12, "sm": 6, "md": 3, "lg": 2},
            )
            for label, campo in campos
        ],
        gutter="md",
        mb="lg",
        align="flex-end",
    )


def metric_card(label: str, value, delta: str | None = None, value_size: str = "xl") -> dmc.Paper:
    # value aceita string (caso comum: número curto, ex: "R$ 2,40") ou já um
    # componente pronto (ex: um dmc.Text com spans com pesos diferentes,
    # tipo "código em negrito | descrição normal") — nesse segundo caso o
    # chamador já controla peso/tamanho, então não embrulha de novo.
    valor_node = dmc.Text(value, size=value_size, fw=700) if isinstance(value, str) else value
    children = [
        dmc.Text(label, size="sm", c="dimmed"),
        valor_node,
    ]
    if delta:
        children.append(dmc.Text(delta, size="xs", c="dimmed"))
    return dmc.Paper(children, withBorder=True, radius="md", p="md")


def metric_row(*cards, cols: dict | None = None) -> dmc.SimpleGrid:
    cols = cols or {"base": 1, "sm": 2, "md": 3}
    return dmc.SimpleGrid(list(cards), cols=cols, spacing="md", mb="md")


def data_table(df, style_data_conditional=None, page_size: int = 20, filterable: bool = True) -> dmc.Paper:
    # dash_table.DataTable não faz parte do Mantine — não herda tema/fonte
    # sozinho. Os style_* apontam pras variáveis CSS que o próprio Mantine
    # já expõe (--mantine-color-*, --mantine-font-*) em vez de valores
    # nossos, pra bater com o resto da UI (mesma fonte/tamanho dos dmc.Text,
    # cores acompanhando o tema automaticamente). style_as_list_view tira as
    # bordas verticais entre células (visual de "grade de planilha"),
    # deixando só um traço horizontal por linha — mais parecido com uma
    # dmc.Table do que com um grid do Excel.
    table = dash_table.DataTable(
        data=df.to_dict("records"),
        columns=[{"name": c, "id": c} for c in df.columns],
        page_size=page_size,
        sort_action="native",
        filter_action="native" if filterable else "none",
        style_as_list_view=True,
        style_table={"overflowX": "auto"},
        style_cell={
            "textAlign": "left",
            "padding": "10px 14px",
            "fontFamily": "var(--mantine-font-family)",
            "fontSize": "var(--mantine-font-size-sm)",
            "backgroundColor": "var(--mantine-color-body)",
            "color": "var(--mantine-color-text)",
            "borderBottom": "1px solid var(--mantine-color-default-border)",
        },
        style_header={
            "fontFamily": "var(--mantine-font-family)",
            "fontSize": "var(--mantine-font-size-sm)",
            "fontWeight": 600,
            "backgroundColor": "var(--mantine-color-body)",
            "color": "var(--mantine-color-text)",
            "borderBottom": "2px solid var(--mantine-color-default-border)",
        },
        style_filter={
            "fontFamily": "var(--mantine-font-family)",
            "fontSize": "var(--mantine-font-size-sm)",
            "backgroundColor": "var(--mantine-color-body)",
            "color": "var(--mantine-color-text)",
            "borderBottom": "1px solid var(--mantine-color-default-border)",
        },
        style_data_conditional=style_data_conditional or [],
    )
    return dmc.Paper(table, withBorder=True, radius="md", p="sm")


def info_box(mensagem: str) -> dmc.Alert:
    return dmc.Alert(mensagem, variant="light", radius="md", mb="md", color="brand")
