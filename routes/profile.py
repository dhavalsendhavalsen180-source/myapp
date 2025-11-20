from flask import Blueprint, render_template, session
import sqlite3

profile_bp = Blueprint("profile", __name__, url_prefix="/profile")

@profile_bp.route("/<username>")
def profile(username):
    conn = sqlite3.connect("database.db")
    c = conn.cursor()

    # user info
    c.execute("SELECT id, username FROM users WHERE username=?", (username,))
    user = c.fetchone()
    if not user:
        return "User not found"

    user_id = user[0]

    # user posts
    c.execute("SELECT id FROM posts WHERE user_id=? ORDER BY id DESC", (user_id,))
    posts = c.fetchall()

    # followers count
    c.execute("SELECT COUNT(*) FROM follows WHERE following_id=?", (user_id,))
    followers = c.fetchone()[0]

    # following count
    c.execute("SELECT COUNT(*) FROM follows WHERE follower_id=?", (user_id,))
    following = c.fetchone()[0]

    conn.close()

    return render_template(
        "profile.html",
        user=user,
        posts=posts,
        followers=followers,
        following=following,
        current_user=session.get("user")
    )
