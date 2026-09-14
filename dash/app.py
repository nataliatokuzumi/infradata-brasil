import dash
import dash_mantine_components as dmc
from dash import ALL, Dash, Input, Output, callback, ctx, dcc
from dash_iconify import DashIconify

import gold

# Templates Plotly com paleta/fontes do Mantine (usados nos px.line/px.bar
# das páginas) — sem isso os gráficos ficavam com o visual genérico do
# Plotly, destoando do resto da UI agora que o app usa Mantine.
dmc.add_figure_templates(default="mantine_light")

# Intervalo de datas disponível na gold inteira (não só no item filtrado) —
# calculado uma vez no startup do processo (não muda a cada request, os
# dados só viram trimestralmente) pra compor o header.
_periodo = gold.query("select min(period_start) as inicio, max(period_start) as fim from dim_data_referencia")
_inicio = gold.formatar_periodo(_periodo["inicio"].iloc[0])
_fim = gold.formatar_periodo(_periodo["fim"].iloc[0])

NOME_APP = "Dashboard de Análise de Preços do SICRO"
SUBTITULO_APP = f"Dados disponíveis de {_inicio} a {_fim}  ·  Fonte: DNIT"
ICONE_APP = "tabler:building-bridge-2"

app = Dash(__name__, use_pages=True, suppress_callback_exceptions=True, title=f"{NOME_APP} | {SUBTITULO_APP}")
server = app.server  # exposto pro entrypoint de produção (gunicorn), ver Dockerfile


def _navbar_links():
    return dmc.Stack(
        [
            dmc.NavLink(
                id={"type": "navlink", "path": page["relative_path"]},
                label=page["name"],
                href=page["relative_path"],
                leftSection=DashIconify(icon="tabler:chart-histogram", width=18),
                variant="filled",
                fw=600,
            )
            for page in dash.page_registry.values()
            # Início não aparece no menu (ver pages/0_home.py, que continua
            # registrada e acessível direto por "/", só não tem mais link
            # no menu).
            if page["relative_path"] != "/"
        ],
        gap=4,
    )


@callback(
    Output({"type": "navlink", "path": ALL}, "active"),
    Input("url", "pathname"),
)
def _marcar_link_ativo(pathname):
    # id de cada NavLink carrega o próprio path (pattern-matching) — o
    # link ativo é só o que bate com a URL atual, dinamicamente conforme
    # páginas são adicionadas/removidas do menu.
    return [item["id"]["path"] == pathname for item in ctx.outputs_list]


app.layout = dmc.MantineProvider(
    # forceColorScheme="light": a página fica sempre no tema claro, mesmo
    # com o SO/navegador em modo escuro — por isso não tem mais
    # ColorSchemeToggle no header (o toggle não teria efeito nenhum com o
    # tema forçado).
    forceColorScheme="light",
    children=dmc.AppShell(
        [
            dcc.Location(id="url", refresh=False),
            dmc.AppShellHeader(
                dmc.Group(
                    [
                        DashIconify(icon=ICONE_APP, width=32, color="var(--mantine-color-blue-6)"),
                        dmc.Stack(
                            [
                                dmc.Text(NOME_APP, fw=700, size="lg", lh=1.2),
                                dmc.Text(SUBTITULO_APP, c="dimmed", size="xs", lh=1.2),
                            ],
                            gap=0,
                        ),
                    ],
                    gap="sm",
                    h="100%",
                    px="lg",
                    wrap="nowrap",
                ),
            ),
            dmc.AppShellNavbar(
                [
                    # bloco de marca no topo do menu, separado dos links por
                    # um Divider — mesmo padrão do header (ícone + nome),
                    # só que compacto.
                    dmc.Group(
                        [
                            DashIconify(icon=ICONE_APP, width=22, color="var(--mantine-color-blue-6)"),
                            dmc.Text("SICRO", fw=700, size="sm"),
                        ],
                        gap="xs",
                        px="sm",
                        py="md",
                    ),
                    dmc.Divider(mb="sm"),
                    _navbar_links(),
                ],
                p="sm",
            ),
            dmc.AppShellMain(dash.page_container),
        ],
        header={"height": 74},
        navbar={"width": 260, "breakpoint": "sm"},
        padding="md",
    ),
)

if __name__ == "__main__":
    app.run(host="0.0.0.0", port=8501, debug=False)
