import hmac
from urllib.parse import urlsplit

from flask import redirect, render_template, request, session, url_for

from app import throttle


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
        address = throttle.client_address()
        wait = throttle.retry_after(address)
        if wait:
            # Checked before the password, so a locked-out client learns
            # nothing from guesses made while it waits.
            minutes = max(1, (wait + 59) // 60)
            body = render_template(
                "login.html",
                error=f"Too many wrong passwords. Try again in {minutes} minute{'s' if minutes != 1 else ''}.",
                next_path=request.form.get("next", ""),
            )
            return body, 429, {"Retry-After": str(wait)}
        if not UI_PASSWORD:
            error = "Site password is not configured (set SPEEDHIVE_UI_PASSWORD)."
        elif hmac.compare_digest(request.form.get("password", "").encode(), UI_PASSWORD.encode()):
            throttle.record_success(address)
            # A fresh session on login, so a cookie planted before it can't ride along.
            session.clear()
            session["authenticated"] = True
            return redirect(_safe_next(request.form.get("next")) or url_for("index"))
        else:
            throttle.record_failure(address)
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
