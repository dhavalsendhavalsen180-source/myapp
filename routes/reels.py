import os
import uuid
import sqlite3
from datetime import datetime
from flask import Blueprint, render_template, request, session, redirect, jsonify

reels_bp = Blueprint("reels", __name__, url_prefix="/reels")

UPLOAD_FOLDER = "static/reels"
os.makedirs(UPLOAD_FOLDER, exist_ok=True)

ALLOWED_VIDEO_EXT = {"mp4", "webm", "mov", "mkv"}


# ===============================
# ✅ DB CONNECTION
# ===============================
def get_conn():
    conn = sqlite3.connect("database.db")
    conn.row_factory = sqlite3.Row
    return conn


# ===============================
# ✅ DB INIT + AUTO UPGRADE
# ===============================
def init_reels_db():
    conn = get_conn()
    c = conn.cursor()

    # reels table
    c.execute("""
        CREATE TABLE IF NOT EXISTS reels (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            user_id INTEGER,
            caption TEXT,
            video_path TEXT,
            likes INTEGER DEFAULT 0,
            saves INTEGER DEFAULT 0,
            shares INTEGER DEFAULT 0,
            comments_count INTEGER DEFAULT 0,
            created_at TEXT
        )
    """)

    # likes table
    c.execute("""
        CREATE TABLE IF NOT EXISTS reel_likes (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            reel_id INTEGER,
            user_id INTEGER,
            created_at TEXT DEFAULT CURRENT_TIMESTAMP,
            UNIQUE(reel_id, user_id)
        )
    """)

    # comments table
    c.execute("""
        CREATE TABLE IF NOT EXISTS reel_comments (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            reel_id INTEGER,
            user_id INTEGER,
            comment TEXT,
            created_at TEXT DEFAULT CURRENT_TIMESTAMP
        )
    """)

    # saves table
    c.execute("""
        CREATE TABLE IF NOT EXISTS reel_saves (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            reel_id INTEGER,
            user_id INTEGER,
            created_at TEXT DEFAULT CURRENT_TIMESTAMP,
            UNIQUE(reel_id, user_id)
        )
    """)

    conn.commit()

    # ===============================
    # AUTO ADD MISSING COLUMNS (SAFE)
    # ===============================
    c.execute("PRAGMA table_info(reels)")
    cols = [r["name"] for r in c.fetchall()]

    if "created_at" not in cols:
        c.execute("ALTER TABLE reels ADD COLUMN created_at TEXT")
    if "saves" not in cols:
        c.execute("ALTER TABLE reels ADD COLUMN saves INTEGER DEFAULT 0")
    if "shares" not in cols:
        c.execute("ALTER TABLE reels ADD COLUMN shares INTEGER DEFAULT 0")
    if "comments_count" not in cols:
        c.execute("ALTER TABLE reels ADD COLUMN comments_count INTEGER DEFAULT 0")

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
# 🎬 REELS FEED PAGE (INSTAGRAM STYLE)
# ===============================
@reels_bp.route("/")
def reels_page():
    init_reels_db()

    conn = get_conn()
    c = conn.cursor()

    c.execute("""
        SELECT reels.id, reels.user_id, reels.caption, reels.video_path,
               reels.likes, reels.saves, reels.shares, reels.comments_count,
               reels.created_at, reels.audio_name,
               users.username
        FROM reels
        JOIN users ON reels.user_id = users.id
        ORDER BY reels.id DESC
    """)

    reels = []
    for r in c.fetchall():
        created_at = r["created_at"] or ""

        reels.append({
            "id": r["id"],
            "user_id": r["user_id"],
            "username": r["username"],
            "caption": r["caption"] or "",
            "video_path": r["video_path"],
            "likes": r["likes"],
            "saves": r["saves"],
            "shares": r["shares"],
            "comments_count": r["comments_count"],
            "created_at": created_at, "audio_name": r["audio_name"]
        })

    conn.close()

    return render_template("reels_feed.html", reels=reels, current_user=get_user_id())


# ===============================
# ⬆️ UPLOAD REEL
# ===============================
@reels_bp.route("/upload", methods=["GET", "POST"])
def upload_reel():
    init_reels_db()

    if "user_id" not in session:
        return redirect("/auth/login")

    if request.method == "GET":
        return render_template("reels_upload.html")

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

    conn = get_conn()
    c = conn.cursor()

    c.execute("""
        INSERT INTO reels (user_id, caption, video_path, audio_name, created_at)
        VALUES (?,?,?,?,?)
    """, (uid, caption, new_name, "Original Audio", datetime.now().strftime("%Y-%m-%d %H:%M:%S")))

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

    conn = get_conn()
    c = conn.cursor()

    c.execute("SELECT id FROM reel_likes WHERE reel_id=? AND user_id=?", (reel_id, uid))
    row = c.fetchone()

    if row:
        c.execute("DELETE FROM reel_likes WHERE reel_id=? AND user_id=?", (reel_id, uid))
        c.execute("UPDATE reels SET likes = likes - 1 WHERE id=? AND likes > 0", (reel_id,))
        action = "unliked"
    else:
        c.execute("INSERT INTO reel_likes (reel_id, user_id) VALUES (?,?)", (reel_id, uid))
        c.execute("UPDATE reels SET likes = likes + 1 WHERE id=?", (reel_id,))
        action = "liked"

    conn.commit()

    c.execute("SELECT likes FROM reels WHERE id=?", (reel_id,))
    count = c.fetchone()["likes"]

    conn.close()

    return jsonify({"ok": True, "action": action, "count": count})


# ===============================
# 🔖 SAVE / UNSAVE REEL (AJAX)
# ===============================
@reels_bp.route("/save_toggle/<int:reel_id>", methods=["POST"])
def save_toggle(reel_id):
    uid = session.get("user_id")
    if not uid:
        return {"ok": False}

    conn = sqlite3.connect(DB_NAME)
    c = conn.cursor()

    c.execute("SELECT id FROM reel_saves WHERE user_id=? AND reel_id=?", (uid, reel_id))
    exists = c.fetchone()

    if exists:
        c.execute("DELETE FROM reel_saves WHERE user_id=? AND reel_id=?", (uid, reel_id))
        state = "removed"
    else:
        c.execute("INSERT INTO reel_saves (user_id, reel_id) VALUES (?,?)", (uid, reel_id))
        state = "saved"

    conn.commit()
    conn.close()

    return {"ok": True, "state": state}

# ===============================
# 📤 SHARE REEL (COUNT)
# ===============================
@reels_bp.route("/share/<int:reel_id>", methods=["POST"])
def share_reel(reel_id):
    init_reels_db()

    conn = get_conn()
    c = conn.cursor()

    c.execute("UPDATE reels SET shares = shares + 1 WHERE id=?", (reel_id,))
    conn.commit()

    c.execute("SELECT shares FROM reels WHERE id=?", (reel_id,))
    shares = c.fetchone()["shares"]

    conn.close()

    return jsonify({"ok": True, "shares": shares})


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

    conn = get_conn()
    c = conn.cursor()

    c.execute("""
        INSERT INTO reel_comments (reel_id, user_id, comment)
        VALUES (?,?,?)
    """, (reel_id, uid, comment))

    c.execute("UPDATE reels SET comments_count = comments_count + 1 WHERE id=?", (reel_id,))

    conn.commit()
    conn.close()

    return jsonify({"ok": True})


# ===============================
# 💬 GET COMMENTS (AJAX)
# ===============================
@reels_bp.route("/comments/<int:reel_id>")
def get_comments(reel_id):
    init_reels_db()

    conn = get_conn()
    c = conn.cursor()

    c.execute("""
        SELECT reel_comments.id, reel_comments.comment, reel_comments.created_at,
               users.username, reel_comments.user_id
        FROM reel_comments
        JOIN users ON reel_comments.user_id = users.id
        WHERE reel_comments.reel_id=?
        ORDER BY reel_comments.id DESC
        LIMIT 50
    """, (reel_id,))

    comments = []
    for r in c.fetchall():
        comments.append({
            "id": r["id"],
            "username": r["username"],
            "user_id": r["user_id"],
            "comment": r["comment"],
            "created_at": r["created_at"]
        })

    conn.close()
    return jsonify({"ok": True, "comments": comments})


# ===============================
# 🗑 DELETE COMMENT (OWNER ONLY)
# ===============================
@reels_bp.route("/comment_delete/<int:comment_id>", methods=["POST"])
def delete_comment(comment_id):
    init_reels_db()

    if "user_id" not in session:
        return jsonify({"ok": False, "error": "login required"})

    uid = get_user_id()

    conn = get_conn()
    c = conn.cursor()

    c.execute("SELECT reel_id, user_id FROM reel_comments WHERE id=?", (comment_id,))
    row = c.fetchone()

    if not row:
        conn.close()
        return jsonify({"ok": False, "error": "not found"})

    reel_id = row["reel_id"]
    owner_id = row["user_id"]

    if owner_id != uid:
        conn.close()
        return jsonify({"ok": False, "error": "not allowed"})

    c.execute("DELETE FROM reel_comments WHERE id=?", (comment_id,))
    c.execute("UPDATE reels SET comments_count = comments_count - 1 WHERE id=? AND comments_count > 0", (reel_id,))

    conn.commit()
    conn.close()

    return jsonify({"ok": True})


# ===============================
# 🗑 DELETE REEL (ONLY OWNER)
# ===============================
@reels_bp.route("/delete/<int:reel_id>", methods=["POST"])
def delete_reel(reel_id):
    init_reels_db()

    if "user_id" not in session:
        return redirect("/auth/login")

    uid = get_user_id()

    conn = get_conn()
    c = conn.cursor()

    c.execute("SELECT video_path, user_id FROM reels WHERE id=?", (reel_id,))
    row = c.fetchone()

    if not row:
        conn.close()
        return redirect("/reels")

    video_path = row["video_path"]
    owner_id = row["user_id"]

    if owner_id != uid:
        conn.close()
        return redirect("/reels")

    try:
        os.remove(os.path.join(UPLOAD_FOLDER, video_path))
    except:
        pass

    c.execute("DELETE FROM reel_likes WHERE reel_id=?", (reel_id,))
    c.execute("DELETE FROM reel_comments WHERE reel_id=?", (reel_id,))
    c.execute("DELETE FROM reel_saves WHERE reel_id=?", (reel_id,))
    c.execute("DELETE FROM reels WHERE id=?", (reel_id,))

    conn.commit()
    conn.close()

    return redirect("/reels")

################################
@reels_bp.route("/audio")
def reels_by_audio():
    name = request.args.get("name","")

    conn = get_conn()
    c = conn.cursor()

    c.execute("""
        SELECT reels.*, users.username
        FROM reels
        JOIN users ON reels.user_id = users.id
        WHERE audio_name=?
        ORDER BY reels.id DESC
    """, (name,))

    reels = c.fetchall()
    conn.close()

    return render_template("reels_feed.html", reels=reels, current_user=get_user_id())

#######comment###№#############
@reels_bp.route("/comments_page/<int:id>")
def comments_page(id):
    return render_template("reel_comments.html", reel_id=id)
