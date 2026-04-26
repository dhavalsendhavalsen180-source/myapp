import os
import uuid
import sqlite3
from flask import Blueprint, render_template, request, session, redirect, url_for, jsonify
from werkzeug.utils import secure_filename

reels_bp = Blueprint("reels", __name__, url_prefix="/reels")

UPLOAD_FOLDER = "static/reels"
os.makedirs(UPLOAD_FOLDER, exist_ok=True)

ALLOWED_VIDEO_EXT = {"mp4", "webm", "mov", "mkv"}


# ===============================
# ✅ INIT REELS DATABASE
# ===============================
def init_reels_db():
    conn = sqlite3.connect("database.db")
    conn.row_factory = sqlite3.Row
    c = conn.cursor()

    # reels table
    c.execute("""
        CREATE TABLE IF NOT EXISTS reels (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            user_id INTEGER,
            caption TEXT,
            video_path TEXT,
            likes INTEGER DEFAULT 0,
            created_at TEXT DEFAULT CURRENT_TIMESTAMP
        )
    """)

    # reel likes table
    c.execute("""
        CREATE TABLE IF NOT EXISTS reel_likes (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            reel_id INTEGER,
            user_id INTEGER,
            UNIQUE(reel_id, user_id)
        )
    """)

    # reel comments table
    c.execute("""
        CREATE TABLE IF NOT EXISTS reel_comments (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            reel_id INTEGER,
            user_id INTEGER,
            comment TEXT,
            created_at TEXT DEFAULT CURRENT_TIMESTAMP
        )
    """)

    conn.commit()
    conn.close()


# ===============================
# ✅ CHECK VIDEO EXTENSION
# ===============================
def allowed_video(filename):
    return "." in filename and filename.rsplit(".", 1)[1].lower() in ALLOWED_VIDEO_EXT


# ===============================
# ✅ GET CURRENT USER ID
# ===============================
def get_user_id():
    return session.get("user_id", 0)


# ===============================
# 🎬 REELS FEED PAGE
# ===============================
@reels_bp.route("/")
def reels_page():
    init_reels_db()

    conn = sqlite3.connect("database.db")
    conn.row_factory = sqlite3.Row
    conn.row_factory = sqlite3.Row
    c = conn.cursor()

    c.execute("""
        SELECT reels.id, reels.user_id, reels.caption, reels.video_path, reels.likes,
               users.username
        FROM reels
        JOIN users ON reels.user_id = users.id
        ORDER BY reels.id DESC
    """)

    reels = []
    for r in c.fetchall():
        reels.append({
            "id": r["id"],
            "user_id": r["user_id"],
            "username": r["username"],
            "caption": r["caption"],
            "video_path": "/static/reels/" + r["video_path"],
            "likes": r["likes"]
        })

    conn.close()

    return render_template("reels_feed.html", reels=reels, current_user=get_user_id())


# ===============================
# ⬆️ UPLOAD REEL
# ===============================
@reels_bp.route("/upload", methods=["POST"])
def upload_reel():
    init_reels_db()

    if "user_id" not in session:
        return redirect("/auth/login")

    caption = request.form.get("caption", "").strip()
    file = request.files.get("video")

    if not file or file.filename == "":
        return "No video selected", 400

    if not allowed_video(file.filename):
        return "Invalid video format", 400

    ext = file.filename.rsplit(".", 1)[-1].lower()
    new_name = f"{uuid.uuid4().hex}.{ext}"

    save_path = os.path.join(UPLOAD_FOLDER, new_name)
    file.save(save_path)

    uid = get_user_id()

    conn = sqlite3.connect("database.db")
    conn.row_factory = sqlite3.Row
    c = conn.cursor()
    c.execute("INSERT INTO reels (user_id, caption, video_path) VALUES (?,?,?)",
              (uid, caption, new_name))
    conn.commit()
    conn.close()

    return redirect("/reels")


# ===============================
# ❤️ LIKE / UNLIKE REEL (AJAX)
# ===============================
@reels_bp.route("/like_toggle/<int:reel_id>", methods=["POST"])
def like_toggle(reel_id):
    init_reels_db()

    if "user_id" not in session:
        return jsonify({"ok": False, "error": "login required"})

    uid = get_user_id()

    conn = sqlite3.connect("database.db")
    conn.row_factory = sqlite3.Row
    c = conn.cursor()

    # check already liked
    c.execute("SELECT id FROM reel_likes WHERE reel_id=? AND user_id=?", (reel_id, uid))
    row = c.fetchone()

    if row:
        # unlike
        c.execute("DELETE FROM reel_likes WHERE reel_id=? AND user_id=?", (reel_id, uid))
        c.execute("UPDATE reels SET likes = likes - 1 WHERE id=? AND likes > 0", (reel_id,))
        action = "unliked"
    else:
        # like
        c.execute("INSERT INTO reel_likes (reel_id, user_id) VALUES (?,?)", (reel_id, uid))
        c.execute("UPDATE reels SET likes = likes + 1 WHERE id=?", (reel_id,))
        action = "liked"

    # new count
    c.execute("SELECT likes FROM reels WHERE id=?", (reel_id,))
    count = c.fetchone()[0]

    conn.commit()
    conn.close()

    return jsonify({"ok": True, "action": action, "count": count})


# ===============================
# 💬 ADD COMMENT (AJAX)
# ===============================
@reels_bp.route("/comment/<int:reel_id>", methods=["POST"])
def add_comment(reel_id):
    init_reels_db()

    if "user_id" not in session:
        return jsonify({"ok": False, "error": "login required"})

    uid = get_user_id()
    comment = request.form.get("comment", "").strip()

    if not comment:
        return jsonify({"ok": False, "error": "empty comment"})

    conn = sqlite3.connect("database.db")
    conn.row_factory = sqlite3.Row
    c = conn.cursor()

    c.execute("INSERT INTO reel_comments (reel_id, user_id, comment) VALUES (?,?,?)",
              (reel_id, uid, comment))

    conn.commit()
    conn.close()

    return jsonify({"ok": True})


# ===============================
# 💬 GET COMMENTS (AJAX)
# ===============================
@reels_bp.route("/comments/<int:reel_id>")
def get_comments(reel_id):
    init_reels_db()

    conn = sqlite3.connect("database.db")
    conn.row_factory = sqlite3.Row
    conn.row_factory = sqlite3.Row
    c = conn.cursor()

    c.execute("""
        SELECT reel_comments.comment, reel_comments.created_at,
               users.username
        FROM reel_comments
        JOIN users ON reel_comments.user_id = users.id
        WHERE reel_comments.reel_id=?
        ORDER BY reel_comments.id DESC
        LIMIT 50
    """, (reel_id,))

    comments = []
    for r in c.fetchall():
        comments.append({
            "username": r["username"],
            "comment": r["comment"],
            "created_at": r["created_at"]
        })

    conn.close()
    return jsonify({"ok": True, "comments": comments})


# ===============================
# 🗑 DELETE REEL (ONLY OWNER)
# ===============================
@reels_bp.route("/delete/<int:reel_id>", methods=["POST"])
def delete_reel(reel_id):
    init_reels_db()

    if "user_id" not in session:
        return redirect("/auth/login")

    uid = get_user_id()

    conn = sqlite3.connect("database.db")
    conn.row_factory = sqlite3.Row
    c = conn.cursor()

    c.execute("SELECT video_path, user_id FROM reels WHERE id=?", (reel_id,))
    row = c.fetchone()

    if not row:
        conn.close()
        return redirect("/reels")

    video_path, owner_id = row

    if owner_id != uid:
        conn.close()
        return redirect("/reels")

    # delete file
    try:
        os.remove(os.path.join(UPLOAD_FOLDER, video_path))
    except:
        pass

    # delete db data
    c.execute("DELETE FROM reel_likes WHERE reel_id=?", (reel_id,))
    c.execute("DELETE FROM reel_comments WHERE reel_id=?", (reel_id,))
    c.execute("DELETE FROM reels WHERE id=?", (reel_id,))

    conn.commit()
    conn.close()

    return redirect("/reels")
