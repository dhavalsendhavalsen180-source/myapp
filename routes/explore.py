from flask import Blueprint, render_template, session, request
import sqlite3
import os

explore_bp = Blueprint("explore", __name__, url_prefix="/explore")


# =========================
# EXPLORE PAGE
# =========================
@explore_bp.route("/")
def explore_page():

    conn = sqlite3.connect("database.db")
    conn.row_factory = sqlite3.Row
    c = conn.cursor()

    # USERS
    c.execute("""
        SELECT id, username, photo
        FROM users
        ORDER BY id DESC
    """)
    users = c.fetchall()

    explore_items = []

    # =========================
    # POSTS
    # =========================
    c.execute("""
        SELECT id, user_id
        FROM posts
        ORDER BY id DESC
    """)

    posts_raw = c.fetchall()

    for p in posts_raw:

        c.execute("""
            SELECT image_path
            FROM post_images
            WHERE post_id=?
            LIMIT 1
        """, (p["id"],))

        img = c.fetchone()

        if img:
            explore_items.append({
                "type": "post",
                "id": p["id"],
                "media": img["image_path"]
            })

    # =========================
    # REELS
    # =========================
    c.execute("""
        SELECT id, video_path
        FROM reels
        ORDER BY id DESC
    """)

    reels = c.fetchall()

    for r in reels:

        explore_items.append({
            "type": "reel",
            "id": r["id"],
            "media": "/static/uploads/reels/" + r["video_path"]
        })

    conn.close()

    # MIX ORDER
    explore_items = sorted(
        explore_items,
        key=lambda x: x["id"],
        reverse=True
    )

    # =========================
    # CURRENT USER PHOTO
    # =========================
    current_user = session.get("user_id")

    jpg = f"static/profile/user_{current_user}.jpg"
    png = f"static/profile/user_{current_user}.png"
    jpeg = f"static/profile/user_{current_user}.jpeg"

    if os.path.exists(jpg):
        current_user_photo = "/" + jpg

    elif os.path.exists(png):
        current_user_photo = "/" + png

    elif os.path.exists(jpeg):
        current_user_photo = "/" + jpeg

    else:
        current_user_photo = "/static/default_dp.png"

    return render_template(
        "explore.html",
        users=users,
        explore_items=explore_items,
        current_user=current_user,
        current_user_photo=current_user_photo
    )


# =========================
# SEARCH PAGE
# =========================
@explore_bp.route("/search")
def explore_search():

    q = request.args.get("q", "").strip()

    conn = sqlite3.connect("database.db")
    conn.row_factory = sqlite3.Row
    c = conn.cursor()

    users = []

    if q:
        c.execute("""
            SELECT id, username, photo
            FROM users
            WHERE username LIKE ?
            ORDER BY username ASC
        """, (f"%{q}%",))

        users = c.fetchall()

    conn.close()

    return render_template(
        "search.html",
        users=users,
        query=q
    )
