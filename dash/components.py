"""Components reused across pages, built on top of Dash Mantine Components
to match the look of the reference example
(financial-dashboard-example.plotly.app) — cards (Paper), responsive grid,
typography and light/dark theme all come from Mantine. dash_table.DataTable
is still used for tables (native sort/filter/conditional styling that
dmc.Table doesn't have), just now themed with Mantine's own CSS variables
instead of our own tokens, to follow the theme toggle without duplicating
logic."""
import dash_mantine_components as dmc
from dash import dash_table, html

# Infradata Brasil brand palette (same colors as the logo in
# dash/assets/logo-mark*.svg) — single source of truth for any chart or
# component that needs a "brand" color instead of a semantic data color
# (e.g. the RdYlGn up/down scale in Maiores Variações is deliberately still
# semantic, doesn't use this palette).
BRAND = {
    "tinta": "#17253F",  # ink — logo structure, brand text
    "ferrugem": "#AD5A1E",  # rust — accent, Mantine theme's primary color
    "cianotipo": "#0E2A45",  # cyanotype navy — footer/blueprint background
    "papel": "#F4EFE4",  # drafting paper
    "linha_clara": "#EAF3FA",  # light line — logo strokes on dark background
    "barra_ambar": "#E6A94F",  # amber bar — logo bars on dark background
}


def page_header(titulo: str, caption: str | list) -> list:
    return [
        dmc.Title(titulo, order=2),
        dmc.Text(caption, c="dimmed", size="sm", mb="md"),
    ]


def limpar_filtros_button(component_id: str):
    return dmc.Button("Limpar filtros", id=component_id, n_clicks=0, variant="light", size="sm", mb="md")


def filter_row(*campos) -> dmc.Grid:
    """Each campo is (label, component) — becomes one column in a responsive
    grid, equivalent to st.columns(n). An empty label skips the helper's
    <label> (used when the Mantine component itself already renders its own
    internal label via the `label=` prop, e.g. dmc.Select). align="flex-end"
    aligns every column to the baseline — that's what makes a button with
    no label (e.g. "Limpar filtros") line up at the same height as the
    other filters' input box, which have a real label above them."""
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
    # value accepts either a string (common case: short number, e.g. "R$
    # 2,40") or an already-built component (e.g. a dmc.Text with spans of
    # different weights, like "bold code | normal description") — in that
    # second case the caller already controls weight/size, so it isn't
    # wrapped again.
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
    # dash_table.DataTable isn't part of Mantine — it doesn't inherit
    # theme/font on its own. The style_* dicts point at the CSS variables
    # Mantine itself already exposes (--mantine-color-*, --mantine-font-*)
    # instead of our own values, to match the rest of the UI (same
    # font/size as dmc.Text, colors following the theme automatically).
    # style_as_list_view removes the vertical borders between cells
    # ("spreadsheet grid" look), leaving just one horizontal line per row —
    # closer to a dmc.Table than to an Excel grid.
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
