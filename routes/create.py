# routes/create.py
from flask import Blueprint, render_template, request, redirect, session, flash, url_for, send_from_directory
import os, uuid, sqlite3, shutil
from werkzeug.utils import secure_filename

create_bp = Blueprint("create", __name__, url_prefix="/create")

DB_NAME = "database.db"

UPLOAD_REELS_DIR = os.path.join("static", "uploads", "reels")
UPLOAD_POSTS_DIR = os.path.join("static", "uploads", "posts")
UPLOAD_STORY_DIR = os.path.join("static", "uploads", "stories")

EDITOR_TEMP_DIR = os.path.join("static", "editor_temp")

os.makedirs(UPLOAD_REELS_DIR, exist_ok=True)
os.makedirs(UPLOAD_POSTS_DIR, exist_ok=True)
os.makedirs(UPLOAD_STORY_DIR, exist_ok=True)
os.makedirs(EDITOR_TEMP_DIR, exist_ok=True)


def get_conn():
    conn = sqlite3.connect(DB_NAME)
    conn.row_factory = sqlite3.Row
    return conn


# ===============================
# 🎥 CREATE HOME (CAMERA UI)
# ===============================
@create_bp.route("/")
def create_home():
    if "user_id" not in session:
        return redirect("/auth/login")

    return render_template("create/index.html")


# ===============================
# ✂️ EDITOR PAGE
# ===============================
@create_bp.route("/editor", methods=["GET", "POST"])
def editor():
    if "user_id" not in session:
        return redirect("/auth/login")

    # Upload from Create -> to open in editor
    if request.method == "POST" and request.files.get("media"):
        f = request.files.get("media")
        filename = secure_filename(f.filename)

        if not filename:
            flash("Invalid file", "error")
            return redirect("/create")

        newname = f"{uuid.uuid4().hex}_{filename}"
        save_path = os.path.join(EDITOR_TEMP_DIR, newname)
        f.save(save_path)

        return redirect(url_for("create.editor", media_path=newname))

    # Exported final media_path from editor
    if request.method == "POST" and request.files.get("export"):
        f = request.files.get("export")
        filename = secure_filename(f.filename) or "export.webm"

        newname = f"{uuid.uuid4().hex}_{filename}"
        save_path = os.path.join(EDITOR_TEMP_DIR, newname)
        f.save(save_path)

        return redirect(url_for("create.publish", media_path=newname))

    media_path = request.args.get("media_path", "")
    mode = request.args.get("mode", "post")

    return render_template("create/editor.html", media_path=media_path, mode=mode)


# ===============================
# 🚀 PUBLISH PAGE
# ===============================
@create_bp.route("/publish", methods=["GET", "POST"])
def publish():
    if "user_id" not in session:
        return redirect("/auth/login")

    if request.method == "POST":
        media_path = request.form.get("media_path", "")
        caption = request.form.get("caption", "").strip()
        hashtags = request.form.get("hashtags", "").strip()
        location = request.form.get("location", "").strip()
        mode = request.form.get("mode", "post").strip()

        user_id = session.get("user_id")

        if not media_path:
            flash("No media selected", "error")
            return redirect("/create")

        src = os.path.join(EDITOR_TEMP_DIR, media_path)
        if not os.path.exists(src):
            flash("File missing in editor temp", "error")
            return redirect("/create")

        # Decide destination folder
        if mode == "reel":
            dest_folder = UPLOAD_REELS_DIR
        elif mode == "story":
            dest_folder = UPLOAD_STORY_DIR
        else:
            dest_folder = UPLOAD_POSTS_DIR

        dest_name = f"{uuid.uuid4().hex}_{media_path}"
        dest = os.path.join(dest_folder, dest_name)

        try:
            os.replace(src, dest)
        except:
            shutil.copy(src, dest)

        # DB SAVE
        conn = get_conn()
        c = conn.cursor()

        # POSTS TABLE
        c.execute("""
            CREATE TABLE IF NOT EXISTS posts (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                user_id INTEGER,
                caption TEXT,
                created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
            )
        """)

        # POST IMAGES TABLE
        c.execute("""
            CREATE TABLE IF NOT EXISTS post_images (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                post_id INTEGER,
                image_path TEXT
            )
        """)

        # REELS TABLE
        c.execute("""
            CREATE TABLE IF NOT EXISTS reels (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                user_id INTEGER,
                caption TEXT,
                hashtags TEXT,
                location TEXT,
                video_path TEXT,
                created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
            )
        """)

        # STORIES TABLE
        c.execute("""
            CREATE TABLE IF NOT EXISTS stories (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                user_id INTEGER,
                media_path TEXT,
                created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                expires_at TIMESTAMP
            )
        """)

        # SAVE ACCORDING TO MODE
        if mode == "reel":
            db_path = "/static/uploads/reels/" + dest_name
            c.execute("""
                INSERT INTO reels (user_id, caption, hashtags, location, video_path)
                VALUES (?, ?, ?, ?, ?)
            """, (user_id, caption, hashtags, location, db_path))

            conn.commit()
            conn.close()

            flash("Reel published successfully!", "success")
            return redirect("/reels")

        elif mode == "story":
            db_path = "/static/uploads/stories/" + dest_name
            c.execute("""
                INSERT INTO stories (user_id, media_path, expires_at)
                VALUES (?, ?, datetime('now','+24 hours'))
            """, (user_id, db_path))

            conn.commit()
            conn.close()

            flash("Story uploaded successfully!", "success")
            return redirect("/posts/feed")

        else:
            # Post mode
            c.execute("INSERT INTO posts (user_id, caption) VALUES (?, ?)", (user_id, caption))
            post_id = c.lastrowid

            db_path = "/static/uploads/posts/" + dest_name
            c.execute("INSERT INTO post_images (post_id, image_path) VALUES (?, ?)", (post_id, db_path))

            conn.commit()
            conn.close()

            flash("Post published successfully!", "success")
            return redirect("/posts/feed")

    media_path = request.args.get("media_path", "")
    mode = request.args.get("mode", "post")

    return render_template("create/publish.html", media_path=media_path, mode=mode)


# ===============================
# 📁 SERVE TEMP FILES
# ===============================
@create_bp.route("/editor_temp/<path:fn>")
def editor_temp(fn):
    return send_from_directory(EDITOR_TEMP_DIR, fn)
