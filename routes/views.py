from flask import Blueprint, render_template, session
import sqlite3

posts_bp = Blueprint("posts_bp", __name__, template_folder="../templates")

DB_NAME = "database.db"

@posts_bp.route("/feed")
def feed():

    current = session.get("user_id")

    photo = "/static/default_dp.png"

    if current:
        conn = sqlite3.connect(DB_NAME)
        conn.row_factory = sqlite3.Row
        c = conn.cursor()

        c.execute("SELECT photo FROM users WHERE id=?", (current,))
        row = c.fetchone()

        if row and row["photo"]:
            photo = row["photo"]

        conn.close()

    # Dummy Stories
    stories = [
        {"img": "https://i.pravatar.cc/120?img=15", "user_id": "Rohit"},
        {"img": "https://i.pravatar.cc/120?img=25", "user_id": "Aisha"},
    ]

    # Dummy Posts
    posts = [
        {
            "user_id": "Rohit",
            "user_img": "https://i.pravatar.cc/100?img=12",
            "image": "https://picsum.photos/600/800?random=10",
            "caption": "Weekend mood 🔥"
        }
    ]

    return render_template(
        "feed.html",
        stories=stories,
        posts=posts,
        current_user=current,
        current_user_photo=photo   # ✅ MOST IMPORTANT
    )
