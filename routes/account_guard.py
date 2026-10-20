import os
import sqlite3

from flask import (
    Blueprint,
    request,
    session,
    redirect,
    url_for,
    render_template_string,
    abort,
)

account_guard_bp = Blueprint("account_guard", __name__)

DB_NAME = "database.db"


def get_db():
    conn = sqlite3.connect(DB_NAME)
    conn.row_factory = sqlite3.Row
    return conn


def is_user_blocked(user_id):
    """Return True if a user is suspended or banned."""
    if user_id is None:
        return False

    conn = get_db()
    try:
        row = conn.execute(
            """
            SELECT COALESCE(suspended, 0) AS suspended,
                   COALESCE(banned, 0) AS banned
            FROM users
            WHERE id = ?
            """,
            (user_id,),
        ).fetchone()

        return bool(row and (row["suspended"] or row["banned"]))
    finally:
        conn.close()


def find_blocked_media_owner(filename):
    """
    Return True if the requested media belongs to a suspended/banned
    user. Unknown or unrelated static files remain accessible.
    """
    filename = filename.replace("\\", "/").lstrip("/")
    basename = os.path.basename(filename)

    conn = get_db()
    try:
        # Story filenames start with the owner's user ID.
        if filename.startswith("stories/"):
            parts = basename.split("_", 1)
            if len(parts) == 2 and parts[0].isdigit():
                row = conn.execute(
                    """
                    SELECT 1 FROM users
                    WHERE id = ?
                      AND (COALESCE(suspended, 0) = 1
                           OR COALESCE(banned, 0) = 1)
                    """,
                    (int(parts[0]),),
                ).fetchone()
                return row is not None

        # Profile photos: match the stored photo path.
        if filename.startswith("profile/"):
            stored_path = "/static/" + filename
            row = conn.execute(
                """
                SELECT 1 FROM users
                WHERE REPLACE(COALESCE(photo, ''), '\\', '/') IN (?, ?)
                  AND (COALESCE(suspended, 0) = 1
                       OR COALESCE(banned, 0) = 1)
                LIMIT 1
                """,
                (stored_path, "static/" + filename),
            ).fetchone()
            return row is not None

        # Reel videos and reel thumbnails.
        if filename.startswith("uploads/reels/"):
            relative = filename[len("uploads/reels/"):]

            if relative.startswith("thumbs/"):
                thumb_name = os.path.basename(relative)
                row = conn.execute(
                    """
                    SELECT 1
                    FROM reels r
                    JOIN users u ON u.id = r.user_id
                    WHERE r.thumbnail = ?
                      AND (COALESCE(u.suspended, 0) = 1
                           OR COALESCE(u.banned, 0) = 1)
                    LIMIT 1
                    """,
                    (thumb_name,),
                ).fetchone()
            else:
                row = conn.execute(
                    """
                    SELECT 1
                    FROM reels r
                    JOIN users u ON u.id = r.user_id
                    WHERE r.video_path = ?
                      AND (COALESCE(u.suspended, 0) = 1
                           OR COALESCE(u.banned, 0) = 1)
                    LIMIT 1
                    """,
                    (relative,),
                ).fetchone()

            return row is not None

        # Post images and video thumbnails.
        if filename.startswith("uploads/posts/"):
            relative = filename[len("uploads/posts/"):]
            is_thumb = relative.startswith("thumbs/")

            if is_thumb:
                thumb_name = os.path.basename(relative)
                source_base = os.path.splitext(
                    thumb_name.removesuffix("_thumb.jpg")
                )[0]

                rows = conn.execute(
                    """
                    SELECT u.suspended, u.banned, pi.image_path
                    FROM post_images pi
                    JOIN posts p ON p.id = pi.post_id
                    JOIN users u ON u.id = p.user_id
                    """
                ).fetchall()

                for row in rows:
                    image_path = (
                        row["image_path"] or ""
                    ).replace("\\", "/")
                    image_base = os.path.splitext(
                        os.path.basename(image_path)
                    )[0]

                    if image_base == source_base and (
                        row["suspended"] or row["banned"]
                    ):
                        return True

                return False

            rows = conn.execute(
                """
                SELECT u.suspended, u.banned, pi.image_path
                FROM post_images pi
                JOIN posts p ON p.id = pi.post_id
                JOIN users u ON u.id = p.user_id
                """
            ).fetchall()

            for row in rows:
                image_path = (
                    row["image_path"] or ""
                ).replace("\\", "/").lstrip("/")

                if image_path.startswith("static/"):
                    image_path = image_path[len("static/"):]

                if image_path == filename and (
                    row["suspended"] or row["banned"]
                ):
                    return True

                if os.path.basename(image_path) == basename and (
                    row["suspended"] or row["banned"]
                ):
                    return True

            return False

        # Legacy post uploads stored directly under uploads/.
        if filename.startswith("uploads/") and "/" not in filename[len("uploads/"):]:
            rows = conn.execute(
                """
                SELECT u.suspended, u.banned, pi.image_path
                FROM post_images pi
                JOIN posts p ON p.id = pi.post_id
                JOIN users u ON u.id = p.user_id
                """
            ).fetchall()

            for row in rows:
                image_path = (
                    row["image_path"] or ""
                ).replace("\\", "/")

                if os.path.basename(image_path) == basename and (
                    row["suspended"] or row["banned"]
                ):
                    return True

        return False
    finally:
        conn.close()


@account_guard_bp.before_app_request
def enforce_account_status():
    # Protect direct URLs to user-uploaded media, even when no user
    # is logged in. Normal CSS, JS, and unrelated static assets work.
    if request.endpoint == "static":
        filename = (request.view_args or {}).get("filename", "")

        if find_blocked_media_owner(filename):
            abort(404)

        return None

    if (
        request.path.startswith("/socket.io/")
        or request.path in (
            "/manifest.json",
            "/service-worker.js",
            "/auth/login",
            "/auth/logout",
            "/account-status",
        )
        or request.path.startswith("/auth/forgot-password")
    ):
        return None

    user_id = session.get("user_id")

    # Admin ID 1 is exempt from account restrictions.
    if not user_id or user_id == 1:
        return None

    conn = get_db()
    try:
        row = conn.execute(
            """
            SELECT COALESCE(suspended, 0) AS suspended,
                   COALESCE(banned, 0) AS banned
            FROM users
            WHERE id = ?
            """,
            (user_id,),
        ).fetchone()
    finally:
        conn.close()

    if not row:
        return None

    if row["banned"] or row["suspended"]:
        session["account_blocked_status"] = (
            "banned" if row["banned"] else "suspended"
        )
        return redirect(url_for("account_guard.account_status"))

    session.pop("account_blocked_status", None)
    return None


@account_guard_bp.route("/account-status")
def account_status():
    user_id = session.get("user_id")

    # Refresh status from the database so restored accounts do not
    # remain stuck on the restricted screen.
    if user_id:
        conn = get_db()
        try:
            row = conn.execute(
                """
                SELECT COALESCE(suspended, 0) AS suspended,
                       COALESCE(banned, 0) AS banned
                FROM users
                WHERE id = ?
                """,
                (user_id,),
            ).fetchone()
        finally:
            conn.close()

        if row and not row["banned"] and not row["suspended"]:
            session.pop("account_blocked_status", None)
            return redirect(url_for("posts.feed"))

        if row:
            session["account_blocked_status"] = (
                "banned" if row["banned"] else "suspended"
            )

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
            <a href="/auth/logout">Log out</a>
        </body>
        </html>
    """, title=title, message=message)
