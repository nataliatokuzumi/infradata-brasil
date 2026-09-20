import os
import secrets

import flask
from dash import Dash
from dash_auth.auth import Auth

LOGIN_ROUTE = "/login"


class SessionAuth(Auth):
    def __init__(self, app: Dash, username: str, password: str):
        self._username = username
        self._password = password

        app.server.secret_key = os.environ.get("DASH_SECRET_KEY") or secrets.token_hex(32)

        super().__init__(app, public_routes=[LOGIN_ROUTE, "/assets/<path:path>"])

    def is_authorized(self) -> bool:
        return flask.session.get("authenticated") is True

    def login_request(self):
        next_path = flask.request.path
        flask.session["next"] = next_path
        return flask.redirect(f"{LOGIN_ROUTE}?next={next_path}")

    def login(self, username: str, password: str) -> bool:
        if username == self._username and password == self._password:
            flask.session["authenticated"] = True
            return True
        return False
