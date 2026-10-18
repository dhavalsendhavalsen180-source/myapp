import sqlite3
from flask import (
    Blueprint, request, session, redirect,
    url_for, render_template_string
)

account_guard_bp = Blueprint("account_guard", __name__)


@account_guard_bp.before_app_request
def enforce_account_status():
    if (
        request.path.startswith("/static/")
        or request.path.startswith("/socket.io/")
        or request.path in (
            "/manifest.json",
            "/service-worker.js",
            "/auth/login",
            "/account-status",
        )
        or request.path.startswith("/auth/forgot-password")
    ):
        return None

    user_id = session.get("user_id")

    # Admin ID 1 is exempt.
    if not user_id or user_id == 1:
        return None

    conn = sqlite3.connect("database.db")
    try:
        row = conn.execute(
            """
            SELECT COALESCE(suspended, 0),
                   COALESCE(banned, 0)
            FROM users
            WHERE id = ?
            """,
            (user_id,),
        ).fetchone()
    finally:
        conn.close()

    if not row:
        return None

    suspended, banned = row

    if banned or suspended:
        session["account_blocked_status"] = (
            "banned" if banned else "suspended"
        )
        return redirect(url_for("account_guard.account_status"))

    return None


@account_guard_bp.route("/account-status")
def account_status():
    status = session.get("account_blocked_status", "restricted")

    if status == "banned":
        title = "Account Banned"
        message = (
            "Your account has been banned. "
            "Please contact the administrator for assistance."
        )
    elif status == "suspended":
        title = "Account Suspended"
        message = (
            "Your account is currently suspended. "
            "Please contact the administrator for assistance."
        )
    else:
        title = "Account Status"
        message = (
            "Your account access is restricted. "
            "Please log in or contact the administrator."
        )

    return render_template_string("""
        <!doctype html>
        <html lang="en">
        <head>
            <meta charset="utf-8">
            <meta name="viewport" content="width=device-width, initial-scale=1">
            <title>{{ title }} - InsChat</title>
        </head>
        <body style="font-family:Arial,sans-serif;max-width:520px;margin:60px auto;padding:24px;text-align:center;">
            <h1>{{ title }}</h1>
            <p>{{ message }}</p>
            <a href="/auth/login">Go to login</a>
        </body>
        </html>
    """, title=title, message=message)
