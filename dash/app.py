import os

import dash
import dash_auth
import dash_mantine_components as dmc
import flask
from dash import ALL, Dash, Input, Output, State, callback, ctx, dcc, html, no_update
from dash_iconify import DashIconify

import gold
from auth import SessionAuth
from logger import get_logger

logger = get_logger(__name__)

dmc.add_figure_templates(default="mantine_light")

_periodo = gold.query("select min(period_start) as inicio, max(period_start) as fim from dim_data_referencia")
_inicio = gold.formatar_periodo(_periodo["inicio"].iloc[0])
_fim = gold.formatar_periodo(_periodo["fim"].iloc[0])

NOME_APP = "Dashboard de Análise de Preços do SICRO"
SUBTITULO_APP = f"Dados disponíveis de {_inicio} a {_fim}  ·  Fonte: DNIT"

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
server = app.server

AUTH_USERNAME = os.environ.get("DASH_AUTH_USERNAME")
AUTH_PASSWORD = os.environ.get("DASH_AUTH_PASSWORD")
auth = SessionAuth(app, AUTH_USERNAME, AUTH_PASSWORD) if AUTH_USERNAME and AUTH_PASSWORD else None


def _navbar_links():
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
    return [item["id"]["path"] == pathname for item in ctx.outputs_list]


def _login_layout():
    next_path = flask.session.get("next", "/")

    return dmc.MantineProvider(
        forceColorScheme="light",
        theme=TEMA_MANTINE,
        children=dmc.Center(
            style={"height": "100vh", "backgroundColor": "#F4EFE4"},
            children=dmc.Paper(
                withBorder=True,
                shadow="sm",
                radius="md",
                p="xl",
                w=360,
                children=dmc.Stack(
                    [
                        dmc.Group(
                            [
                                html.Img(src="/assets/logo-mark.svg", height=40, width=47),
                                dmc.Stack(
                                    [
                                        dmc.Text(
                                            "INFRADATA BRASIL",
                                            fw=800,
                                            size="xs",
                                            c=COR_ACCENT,
                                            style={"letterSpacing": "0.16em"},
                                        ),
                                        dmc.Text(NOME_APP, fw=700, size="sm", c=COR_INK, lh=1.2),
                                    ],
                                    gap=2,
                                ),
                            ],
                            gap="sm",
                            mb="md",
                        ),
                        dmc.TextInput(id="login-username", label="Usuário", placeholder="usuário", required=True),
                        dmc.PasswordInput(id="login-password", label="Senha", placeholder="senha", required=True, n_submit=0),
                        dmc.Text(id="login-error", c="red", size="sm", mih=20),
                        dmc.Button("Entrar", id="login-button", color="brand", fullWidth=True, n_clicks=0),
                        dcc.Store(id="login-next", data=next_path),
                        dcc.Location(id="login-redirect"),
                    ],
                    gap="sm",
                ),
            ),
        ),
    )


def _dashboard_layout():
    return dmc.MantineProvider(
    forceColorScheme="light",
    theme=TEMA_MANTINE,
    children=dmc.AppShell(
        id="appshell",
        children=[
            dcc.Location(id="url", refresh=False),
            dmc.AppShellHeader(
                dmc.Group(
                    [
                        dmc.Burger(id="burger-toggle", opened=False, hiddenFrom="sm", size="sm"),
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
                    dmc.Group(
                        [
                            html.Img(src="/assets/logo-mark.svg", height=28, width=32),
                            dmc.Text("SICRO", fw=800, size="sm", c=COR_INK, style={"letterSpacing": "0.03em"}),
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
        navbar={"width": 260, "breakpoint": "sm", "collapsed": {"mobile": True}},
        footer={"height": 52},
        padding="md",
    ),
    )


def serve_layout():
    if auth and not auth.is_authorized():
        return _login_layout()
    return _dashboard_layout()


app.layout = serve_layout


@dash_auth.public_callback(
    Output("login-error", "children"),
    Output("login-redirect", "href"),
    Input("login-button", "n_clicks"),
    Input("login-password", "n_submit"),
    State("login-username", "value"),
    State("login-password", "value"),
    State("login-next", "data"),
    prevent_initial_call=True,
)
def _fazer_login(n_clicks, n_submit, username, password, next_path):
    if auth and auth.login(username or "", password or ""):
        logger.info(f"[auth] login succeeded for user={username!r}")
        return "", next_path or "/"
    logger.warning(f"[auth] login failed for user={username!r}")
    return "Usuário ou senha inválidos.", no_update


@callback(
    Output("appshell", "navbar"),
    Input("burger-toggle", "opened"),
    State("appshell", "navbar"),
)
def _toggle_mobile_navbar(opened, navbar):
    navbar["collapsed"] = {"mobile": not opened}
    return navbar

if __name__ == "__main__":
    app.run(host="0.0.0.0", port=8501, debug=False)
