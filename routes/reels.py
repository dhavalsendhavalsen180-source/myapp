import os
import uuid
import sqlite3
from datetime import datetime
from flask import Blueprint, render_template, request, session, redirect, jsonify

reels_bp = Blueprint("reels", __name__, url_prefix="/reels")

DB_NAME = "database.db"

UPLOAD_FOLDER = "static/uploads/reels"
os.makedirs(UPLOAD_FOLDER, exist_ok=True)

THUMB_FOLDER = "static/uploads/reels/thumbs"
os.makedirs(THUMB_FOLDER, exist_ok=True)

ALLOWED_VIDEO_EXT = {"mp4", "webm", "mov", "mkv"}


# ===============================
# ✅ DB CONNECTION
# ===============================
def get_conn():
    conn = sqlite3.connect("database.db", timeout=20)
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
    # =========================
# FOLLOW SYSTEM TABLE
# =========================
    c.execute("""
    CREATE TABLE IF NOT EXISTS follows (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        follower_id INTEGER,
        following_id INTEGER,
        created_at TEXT DEFAULT CURRENT_TIMESTAMP,
        UNIQUE(follower_id, following_id)
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
    if "audio_name" not in cols:
        c.execute("ALTER TABLE reels ADD COLUMN audio_name TEXT DEFAULT 'Original Audio'")

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
# 🎬 REELS FEED PAGE (INS STYLE)
# ===============================
@reels_bp.route("/")
def reels_page():
    init_reels_db()

    conn = get_conn()
    c = conn.cursor()

    c.execute("""
        SELECT reels.id, reels.user_id, reels.caption, reels.video_path,
       reels.thumbnail,
               reels.likes, reels.saves, reels.shares, reels.comments_count,
               reels.created_at, reels.audio_name,
               users.username, users.photo
        FROM reels
        JOIN users ON reels.user_id = users.id
        ORDER BY reels.id DESC
    """)

    reels = []
    for r in c.fetchall():
        created_at = r["created_at"] or ""

        c.execute("""
            SELECT 1
            FROM reel_likes
            WHERE reel_id=? AND user_id=?
        """, (r["id"], get_user_id()))

        liked = c.fetchone() is not None

        c.execute("""
            SELECT 1
            FROM follows
            WHERE follower_id=? AND following_id=?
        """, (get_user_id(), r["user_id"]))

        is_following = c.fetchone() is not None

        c.execute("""
            SELECT 1
            FROM reel_saves
            WHERE reel_id=? AND user_id=?
        """, (r["id"], get_user_id()))

        saved = c.fetchone() is not None

        reels.append({
            "id": r["id"],
            "user_id": r["user_id"],
            "username": r["username"],
            "profile_photo": r["photo"],
            "caption": r["caption"] or "",
            "video_path": r["video_path"],
            "thumbnail": r["thumbnail"],
            "likes": r["likes"],
            "liked": liked,
            "following": is_following,
            "saves": r["saves"],
            "saved": saved,
            "shares": r["shares"],
            "comments_count": r["comments_count"],
            "created_at": created_at, "audio_name": r["audio_name"]
        })


    uid = get_user_id()

    conn = get_conn()
    c = conn.cursor()

    c.execute("SELECT photo FROM users WHERE id=?", (uid,))
    user = c.fetchone()

    current_user_photo = "/static/default_dp.png"

    if user and user["photo"]:
        current_user_photo = user["photo"]

    conn.close()

    return render_template(
        "reels_feed.html",
        reels=reels,
        current_user=uid,
        current_user_photo=current_user_photo
    )

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

    # AUTO THUMBNAIL
    thumb_name = f"{uuid.uuid4().hex}.jpg"
    thumb_path = os.path.join(THUMB_FOLDER, thumb_name)

    os.system(
        f'ffmpeg -i "{save_path}" -ss 00:00:01 -vframes 1 "{thumb_path}" -y'
    )


    uid = get_user_id()

    conn = get_conn()
    c = conn.cursor()

    c.execute("""
        INSERT INTO reels (user_id, caption, video_path, thumbnail, audio_name, created_at)
        VALUES (?,?,?,?,?,?)
    """, (uid, caption, new_name, thumb_name, "Original Audio", datetime.now().strftime("%Y-%m-%d %H:%M:%S")))

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
        return jsonify({"ok": False})

    uid = get_user_id()

    conn = sqlite3.connect("database.db", timeout=10)
    conn.row_factory = sqlite3.Row
    c = conn.cursor()

    c.execute("SELECT 1 FROM reel_likes WHERE reel_id=? AND user_id=?", (reel_id, uid))
    liked = c.fetchone()

    if liked:
        c.execute("DELETE FROM reel_likes WHERE reel_id=? AND user_id=?", (reel_id, uid))
        c.execute("UPDATE reels SET likes = CASE WHEN likes > 0 THEN likes - 1 ELSE 0 END WHERE id=?", (reel_id,))
        new_state = False
    else:
        c.execute("INSERT OR IGNORE INTO reel_likes (reel_id, user_id) VALUES (?, ?)", (reel_id, uid))
        c.execute("UPDATE reels SET likes = likes + 1 WHERE id=?", (reel_id,))
        new_state = True

    conn.commit()

    c.execute("SELECT likes FROM reels WHERE id=?", (reel_id,))
    count = c.fetchone()["likes"]

    conn.close()

    return jsonify({
        "ok": True,
        "liked": new_state,
        "count": count
    })


# ===============================
# 🔖 SAVE / UNSAVE REEL (AJAX)
# ===============================
@reels_bp.route("/save_toggle/<int:reel_id>", methods=["POST"])
def save_toggle(reel_id):

    uid = session.get("user_id")

    if not uid:
        return jsonify({"ok": False})

    conn = get_conn()
    c = conn.cursor()

    c.execute(
        "SELECT id FROM reel_saves WHERE user_id=? AND reel_id=?",
        (uid, reel_id)
    )

    exists = c.fetchone()

    if exists:

        c.execute(
            "DELETE FROM reel_saves WHERE user_id=? AND reel_id=?",
            (uid, reel_id)
        )

        c.execute(
            "UPDATE reels SET saves = CASE WHEN saves > 0 THEN saves - 1 ELSE 0 END WHERE id=?",
            (reel_id,)
        )

        saved = False

    else:

        c.execute(
            "INSERT INTO reel_saves (user_id,reel_id) VALUES (?,?)",
            (uid, reel_id)
        )

        c.execute(
            "UPDATE reels SET saves=saves+1 WHERE id=?",
            (reel_id,)
        )

        saved = True

    conn.commit()

    c.execute(
        "SELECT saves FROM reels WHERE id=?",
        (reel_id,)
    )

    count = c.fetchone()["saves"]

    conn.close()

    return jsonify({
        "ok": True,
        "saved": saved,
        "count": count
    })

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
        SELECT rc.id, rc.comment, rc.created_at,
               u.username, u.id as user_id, u.photo
        FROM reel_comments rc
        JOIN users u ON rc.user_id = u.id
        WHERE rc.reel_id=?
        ORDER BY rc.id DESC
        LIMIT 50
    """, (reel_id,))

    comments = []

    for r in c.fetchall():

        # 👇 replies (optional future support)
        replies = []

        comments.append({
            "id": r["id"],
            "username": r["username"],
            "user_id": r["user_id"],
            "text": r["comment"],   # ⚠️ IMPORTANT (text not comment)
            "profile": r["photo"], # 👈 PROFILE PIC
            "likes": 0,
            "replies": replies
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
#//       audio           ✅  //#
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


#==============================================
#             coment                      /
#================================/============
@reels_bp.route("/comments_page/<int:id>")
def comments_page(id):
    return render_template(
        "reel_comments.html",
        reel_id=id,
        current_user=get_user_id()   # 👈 ADD THIS
    )

# ===============================
# ❤️ LIKE COMMENT
# ===============================
@reels_bp.route("/comment_like/<int:id>", methods=["POST"])
def comment_like(id):
    if "user_id" not in session:
        return jsonify({"ok": False})

    # abhi simple dummy (baad me DB bana denge)
    return jsonify({"ok": True, "likes": 1})

# =========================
#   user id
# =========================
@reels_bp.route("/follow/<int:user_id>", methods=["POST"])
def follow_user(user_id):
    uid = session.get("user_id")
    if not uid:
        return jsonify({"ok": False})

    conn = get_conn()
    c = conn.cursor()

    c.execute("SELECT id FROM follows WHERE follower_id=? AND following_id=?", (uid, user_id))
    row = c.fetchone()

    if row:
        c.execute("DELETE FROM follows WHERE follower_id=? AND following_id=?", (uid, user_id))
        following = False
    else:
        c.execute("INSERT INTO follows (follower_id, following_id) VALUES (?,?)", (uid, user_id))
        following = True

    conn.commit()
    conn.close()

    return jsonify({"ok": True, "following": following})

# =========================
# FOLLOWING USERS LIST FIX
# =========================
@reels_bp.route("/api/following_users")
def reels_following_users():

    uid = session.get("user_id")
    if not uid:
        return jsonify({"users": []})

    conn = get_conn()
    c = conn.cursor()

    c.execute("""
        SELECT u.id, u.username, u.photo
        FROM follows f
        JOIN users u ON u.id = f.following_id
        WHERE f.follower_id=?
    """, (uid,))

    users = []

    for r in c.fetchall():

        photo = r["photo"]

        if not photo or str(photo).lower() in ["none", "null", ""]:
            avatar = "/static/default_dp.png"
        elif str(photo).startswith("http"):
            avatar = photo
        elif str(photo).startswith("/static/"):
            avatar = photo
        else:
            avatar = "/static/profile/" + photo

        users.append({
            "id": r["id"],
            "username": r["username"],
            "avatar": avatar
        })

    conn.close()

    return jsonify({"users": users})

# =========================
# SHARE TO USER (DM STYLE)
# =========================
@reels_bp.route("/share_to_user/<int:reel_id>/<int:user_id>", methods=["POST"])
def share_to_user(reel_id, user_id):

    sender = session.get("user_id")

    if not sender:
        return jsonify({"ok": False})

    conn = get_conn()
    c = conn.cursor()

    c.execute("""
        CREATE TABLE IF NOT EXISTS reel_shares (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            sender_id INTEGER,
            receiver_id INTEGER,
            reel_id INTEGER,
            created_at TEXT DEFAULT CURRENT_TIMESTAMP
        )
    """)

    c.execute("""
        INSERT INTO reel_shares (
            sender_id,
            receiver_id,
            reel_id
        )
        VALUES (?,?,?)
    """, (sender, user_id, reel_id))

    conn.commit()
    conn.close()

    return jsonify({"ok": True})
