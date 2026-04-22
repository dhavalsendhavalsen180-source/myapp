from flask import Blueprint, render_template, request, session, redirect, url_for
import sqlite3, os, uuid
from werkzeug.utils import secure_filename
from .reels_db import init_reels_db

reels_bp = Blueprint("reels", __name__, url_prefix="/reels")

# Update: save reels inside static folder
UPLOAD_FOLDER = "static/reels"
os.makedirs(UPLOAD_FOLDER, exist_ok=True)

def get_user_id():
    user_id = session.get("user_id")
    return user_id["id"] if isinstance(user_id, dict) else 0

# ----------------- Reels Feed Page -----------------
@reels_bp.route("/")
def reels_page():
    conn = sqlite3.connect("database.db")
    c = conn.cursor()
    c.execute("SELECT * FROM reels ORDER BY id DESC")
    reels = c.fetchall()
    conn.close()

    return render_template("reels_feed.html", reels=reels)

# ----------------- Upload Reel -----------------
@reels_bp.route("/upload", methods=["POST"])
def upload_reel():
    if "user_id" not in session:
        return redirect("/auth/login")

    caption = request.form.get("caption", "")
    media_path = request.files.get("video")

    if not media_path:
        return "No video selected", 400

    filename = secure_filename(media_path.filename)
    ext = filename.rsplit(".", 1)[-1].lower()
    new_name = f"{uuid.uuid4().hex}.{ext}"

    # Save video in static/reels
    media_path.save(os.path.join(UPLOAD_FOLDER, new_name))

    user_id = get_user_id()

    conn = sqlite3.connect("database.db")
    c = conn.cursor()
    c.execute("INSERT INTO reels (user_id, caption, video_path) VALUES (?,?,?)",
              (user_id, caption, new_name))
    conn.commit()
    conn.close()

    return redirect("/reels")

# ----------------- Like Reel -----------------
@reels_bp.route("/like/<int:id>")
def like_reel(id):
    conn = sqlite3.connect("database.db")
    c = conn.cursor()
    c.execute("UPDATE reels SET likes = likes + 1 WHERE id=?", (id,))
    conn.commit()
    conn.close()
    return "liked"

# ----------------- Init Reels DB -----------------
def init_reels_db():
    conn = sqlite3.connect("database.db")
    c = conn.cursor()
    c.execute("""
        CREATE TABLE IF NOT EXISTS reels (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            user_id INTEGER,
            caption TEXT,
            video_path TEXT,
            likes INTEGER DEFAULT 0,
            comments INTEGER DEFAULT 0,
            shares INTEGER DEFAULT 0,
            saves INTEGER DEFAULT 0
        )
    """)
    conn.commit()
    conn.close()
