from flask import Blueprint, render_template, session, request
import sqlite3

explore_bp = Blueprint("explore", __name__, url_prefix="/explore")

# -----------------------------
# EXPLORE PAGE (GRID + STORIES)
# -----------------------------
@explore_bp.route("/")
def explore_page():
    conn = sqlite3.connect("database.db")
    conn.row_factory = sqlite3.Row
    c = conn.cursor()

    # Fetch users for story-style top bar
    c.execute("SELECT id, username, photo FROM users ORDER BY id DESC")
    users = c.fetchall()

    # Fetch posts for explore grid
    c.execute("SELECT id, user_id FROM posts ORDER BY id DESC")
    posts_raw = c.fetchall()

    posts = []
    for p in posts_raw:
        c.execute("SELECT image_path FROM post_images WHERE post_id=?", (p["id"],))
        imgs = [row["image_path"] for row in c.fetchall()]
        if not imgs:
            imgs = ["noimg.jpg"]

        posts.append({
            "id": p["id"],
            "user_id": p["user_id"],
            "images": imgs
        })

    conn.close()

    return render_template("explore.html",
                           users=users,
                           posts=posts,
                           current_user=session.get("user_id"))

# -----------------------------
# SEARCH USERS PAGE
# -----------------------------
@explore_bp.route("/search")
def explore_search():
    q = request.args.get("q", "").strip()

    conn = sqlite3.connect("database.db")
    conn.row_factory = sqlite3.Row
    c = conn.cursor()

    if q:
        c.execute("SELECT id, username, photo FROM users WHERE username LIKE ?", (f"%{q}%",))
        users = c.fetchall()
    else:
        users = []

    conn.close()

    return render_template("search.html",
                           users=users,
                           query=q)
