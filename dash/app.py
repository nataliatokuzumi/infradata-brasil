import os

import dash
import dash_auth
import dash_mantine_components as dmc
from dash import ALL, Dash, Input, Output, callback, ctx, dcc, html
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

# Paleta da marca Infradata Brasil (ver dash/assets/logo-mark.svg): tinta
# nanquim + ferrugem, papel de prancheta — as mesmas cores do logotipo.
# "brand" vira a cor primária do Mantine (botões, foco de campo). "tinta" é
# o azul-marinho do próprio logotipo (as vigas da ponte), registrado como
# cor Mantine à parte pra dar o "azul da marca" no link ativo do menu
# lateral — em vez do azul genérico padrão do Mantine. Os gráficos NÃO
# seguem essa paleta de propósito — lá a cor é semântica (regime
# tributário, alta/queda de preço), e usar cor de marca ali confundiria
# identidade visual com significado de dado.
COR_INK = "#17253F"
COR_ACCENT = "#AD5A1E"
TEMA_MANTINE = {
    "primaryColor": "brand",
    "colors": {
        "brand": [
            "#FBF1E8", "#F5E1CC", "#EACAA3", "#DDAE78", "#CE9354",
            "#BE7938", "#AD5A1E", "#964E1A", "#7C4015", "#613210",
        ],
        "tinta": [
            "#EDF1F6", "#D3DCE6", "#B7C4D6", "#99ACC5", "#7A93B3",
            "#5C7AA0", "#3A5578", "#2A3F5C", "#1E2E47", "#17253F",
        ],
    },
}

app = Dash(__name__, use_pages=True, suppress_callback_exceptions=True, title="Infradata Brasil")
server = app.server  # exposto pro entrypoint de produção (gunicorn), ver Dockerfile

# Basic Auth via variáveis de ambiente — só liga se as duas estiverem
# setadas, pra não travar o dev local (docker-compose sem elas continua
# abrindo direto). Em produção (Railway, sem Easy Auth nativo como o Azure
# tem), é isso que impede acesso sem login. Credenciais nunca no código —
# mesmo tratamento que a connection string do Storage.
AUTH_USERNAME = os.environ.get("DASH_AUTH_USERNAME")
AUTH_PASSWORD = os.environ.get("DASH_AUTH_PASSWORD")
if AUTH_USERNAME and AUTH_PASSWORD:
    dash_auth.BasicAuth(app, {AUTH_USERNAME: AUTH_PASSWORD})


def _navbar_links():
    # Sem página Início: Análise de Insumos (pages/1_preco_por_item.py)
    # registra path="/" e é a própria página de abertura do app, então
    # todas as páginas registradas aparecem no menu, sem filtro.
    return dmc.Stack(
        [
            dmc.NavLink(
                id={"type": "navlink", "path": page["relative_path"]},
                label=page["name"],
                href=page["relative_path"],
                leftSection=DashIconify(icon="tabler:chart-histogram", width=18),
                variant="filled",
                color="tinta",
                fw=600,
            )
            for page in dash.page_registry.values()
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
    # tema forçado). theme: registra a cor da marca como primária do
    # Mantine (ver TEMA_MANTINE acima).
    forceColorScheme="light",
    theme=TEMA_MANTINE,
    children=dmc.AppShell(
        [
            dcc.Location(id="url", refresh=False),
            dmc.AppShellHeader(
                dmc.Group(
                    [
                        html.Img(src="/assets/logo-mark.svg", height=38, width=45),
                        dmc.Stack(
                            [
                                dmc.Text(
                                    "INFRADATA BRASIL",
                                    fw=800,
                                    size="xs",
                                    c=COR_ACCENT,
                                    style={"letterSpacing": "0.16em"},
                                ),
                                dmc.Text(NOME_APP, fw=700, size="md", c=COR_INK, lh=1.2),
                                dmc.Text(SUBTITULO_APP, c="dimmed", size="xs", lh=1.2),
                            ],
                            gap=2,
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
                    # um Divider — mesmo lockup do logotipo (símbolo +
                    # nome), só que compacto.
                    dmc.Group(
                        [
                            html.Img(src="/assets/logo-mark.svg", height=28, width=32),
                            dmc.Text("INFRADATA", fw=800, size="sm", c=COR_INK, style={"letterSpacing": "0.03em"}),
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
            dmc.AppShellFooter(
                dmc.Group(
                    [
                        dmc.Group(
                            [
                                html.Img(src="/assets/logo-mark-light.svg", height=24, width=28),
                                dmc.Text(
                                    "INFRADATA BRASIL",
                                    fw=700,
                                    size="xs",
                                    c="#EAF3FA",
                                    style={"letterSpacing": "0.1em"},
                                ),
                            ],
                            gap="xs",
                        ),
                        dmc.Text(
                            "Dados públicos do DNIT/SICRO — uso interno de análise de custos.",
                            size="xs",
                            c="#9FBBD3",
                        ),
                    ],
                    justify="space-between",
                    h="100%",
                    px="lg",
                    wrap="wrap",
                ),
                style={"backgroundColor": COR_INK},
            ),
        ],
        header={"height": 82},
        navbar={"width": 260, "breakpoint": "sm"},
        footer={"height": 52},
        padding="md",
    ),
)

if __name__ == "__main__":
    app.run(host="0.0.0.0", port=8501, debug=False)
