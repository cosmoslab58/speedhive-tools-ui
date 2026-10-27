import hmac
from urllib.parse import urlsplit

from flask import redirect, render_template, request, session, url_for


def _safe_next(next_path):
    """A same-site relative path, or None. Browsers strip tabs and newlines
    and read a backslash as a slash, so "/<tab>/evil.com" would land off-site."""
    if not next_path or not next_path.startswith("/") or any(c in next_path for c in "\\\t\r\n"):
        return None
    parts = urlsplit(next_path)
    if parts.scheme or parts.netloc or next_path.startswith("//"):
        return None
    return next_path


def login():
    from app import UI_PASSWORD
    error = None
    if request.method == "POST":
        if not UI_PASSWORD:
            error = "Site password is not configured (set SPEEDHIVE_UI_PASSWORD)."
        elif hmac.compare_digest(request.form.get("password", "").encode(), UI_PASSWORD.encode()):
            # A fresh session on login, so a cookie planted before it can't ride along.
            session.clear()
            session["authenticated"] = True
            return redirect(_safe_next(request.form.get("next")) or url_for("index"))
        else:
            error = "Incorrect password."
    if session.get("authenticated"):
        return redirect(url_for("index"))
    return render_template("login.html", error=error, next_path=request.args.get("next", ""))


def logout():
    session.clear()
    return redirect(url_for("login"))


def register_routes(app):
    app.add_url_rule("/login", "login", login, methods=["GET", "POST"])
    app.add_url_rule("/logout", "logout", logout, methods=["POST"])
