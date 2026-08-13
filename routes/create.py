# routes/create.py
from flask import Blueprint, render_template, request, redirect, session, flash, url_for, send_from_directory
import os, uuid, sqlite3, shutil, json, time
import json, time
import subprocess
from werkzeug.utils import secure_filename

create_bp = Blueprint("create", __name__, url_prefix="/create")

DB_NAME = "database.db"

UPLOAD_REELS_DIR = os.path.join("static", "uploads", "reels")
THUMB_FOLDER = os.path.join("static", "uploads", "reels", "thumbs")
os.makedirs(THUMB_FOLDER, exist_ok=True)
UPLOAD_POSTS_DIR = os.path.join("static", "uploads", "posts")      # ✅ posts folder
UPLOAD_STORY_DIR = os.path.join("static", "stories")    # ✅ story folder

EDITOR_TEMP_DIR = os.path.join("static", "editor_temp")

os.makedirs(UPLOAD_REELS_DIR, exist_ok=True)
os.makedirs(UPLOAD_POSTS_DIR, exist_ok=True)
os.makedirs(UPLOAD_STORY_DIR, exist_ok=True)
os.makedirs(EDITOR_TEMP_DIR, exist_ok=True)


# ===============================
# ✅ DB CONNECTION
# ===============================
def get_conn():
    conn = sqlite3.connect(DB_NAME)
    conn.row_factory = sqlite3.Row
    return conn


# ===============================
# ✅ GET USER ID (FIXED)
# ===============================
def get_user_id():
    uid = session.get("user_id", 0)
    if isinstance(uid, dict):
        return uid.get("id", 0)
    return uid
# ===============================
# 🎵 MIX VIDEO + MUSIC (PART 1)
# ===============================
def mix_audio_with_video(
    video_path,
    music_filename,
    music_start,
    music_end,
    original_volume,
    music_volume
):
    """
    Mix original video audio with selected music.
    """

    if not music_filename:
        return video_path

    music_path = os.path.join(
        "static",
        "music",
        "uploads",
        music_filename
    )

    if not os.path.exists(music_path):
        print("Music file not found:", music_path)
        return video_path

    output_path = os.path.splitext(video_path)[0] + "_mixed.mp4"

    try:

        original_volume = float(original_volume) / 100.0
        music_volume = float(music_volume) / 100.0

        music_start = float(music_start)
        music_end = float(music_end)

    except Exception as e:

        print("Volume parse error:", e)

        original_volume = 1.0
        music_volume = 0.7
        music_start = 0
        music_end = 30
        command = [
        "ffmpeg",
        "-y",
        "-i", video_path,
        "-ss", str(music_start),
        "-to", str(music_end),
        "-i", music_path,
        "-filter_complex",
        (
            f"[0:a]volume={original_volume}[a0];"
            f"[1:a]volume={music_volume}[a1];"
            "[a0][a1]amix=inputs=2:duration=first[aout]"
        ),
        "-map", "0:v",
        "-map", "[aout]",
        "-c:v", "copy",
        "-c:a", "aac",
        "-shortest",
        output_path
    ]
        subprocess.run(
            command,
            check=True,
            stdout=subprocess.PIPE,
            stderr=subprocess.PIPE
        )

        if os.path.exists(output_path):
            os.replace(output_path, video_path)

        return video_path

    except subprocess.CalledProcessError as e:

        print("FFmpeg Error:")
        print(e.stderr.decode(errors="ignore"))

        return video_path

    except Exception as e:

        print("Audio Mix Error:", e)

        return video_path

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

        return redirect(url_for("create.editor", media_path=newname, mode=request.args.get("mode","post")))

    # Exported final media_path from editor
    if request.method == "POST" and request.files.get("export"):
        f = request.files.get("export")
        filename = secure_filename(f.filename) or "export.webm"

        newname = f"{uuid.uuid4().hex}_{filename}"
        save_path = os.path.join(EDITOR_TEMP_DIR, newname)
        f.save(save_path)

        return redirect(
            url_for(
                "create.publish",
                media_path=newname,
                mode=request.args.get("mode", "post"),
                music_id=request.args.get("music_id", ""),
                music_start=request.args.get("music_start", 0),
                music_end=request.args.get("music_end", 30)
            )
        )

    media_path = request.args.get("media_path", "")
    mode = request.args.get("mode", "post")

    music = None

    music_id = request.args.get("music_id")

    if music_id:
        conn = sqlite3.connect(DB_NAME)
        conn.row_factory = sqlite3.Row
        music = conn.execute("SELECT * FROM music WHERE id=?", (music_id,)).fetchone()
        conn.close()


    return render_template("create/editor.html", media_path=media_path, mode=mode, music=music)


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

        music_id = request.form.get("music_id")
        music_start = request.form.get("music_start", 0)
        music_end = request.form.get("music_end", 30)

        original_volume = request.form.get("original_volume", 100)
        music_volume = request.form.get("music_volume", 70)

        user_id = get_user_id()

        if not media_path:
            flash("No media selected", "error")
            return redirect("/create")

        src = os.path.join(EDITOR_TEMP_DIR, media_path)

        if not os.path.exists(src):
            flash("File missing in editor temp", "error")
            return redirect("/create")

        # Destination folder
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
# --------------------------
# MIX AUDIO WITH VIDEO
# --------------------------
        if (
            music_id
            and dest.lower().endswith(
                (".mp4", ".mov", ".webm", ".mkv")
            )
        ):

            conn = get_conn()
            conn.row_factory = sqlite3.Row

            music = conn.execute(
                "SELECT filename FROM music WHERE id=?",
                (music_id,)
            ).fetchone()

            conn.close()

            if music:
                mix_audio_with_video(
                    dest,
                    music["filename"],
                    music_start,
                    music_end,
                    original_volume,
                    music_volume
                )

        conn = get_conn()
        c = conn.cursor()

        thumb_name = None

        if mode == "reel":
            thumb_name = f"{uuid.uuid4().hex}.jpg"
            thumb_path = os.path.join(THUMB_FOLDER, thumb_name)

            subprocess.run([
                "ffmpeg",
                "-y",
                "-i", dest,
                "-ss", "00:00:00.5",
                "-frames:v", "1",
                thumb_path
            ], stdout=subprocess.DEVNULL,
               stderr=subprocess.DEVNULL)

            if not os.path.exists(thumb_path):
                thumb_name = None

        # --------------------------
        # REEL
        # --------------------------
        if mode == "reel":

            c.execute("""
                INSERT INTO reels
                (
                    user_id,
                    caption,
                    video_path,
                    thumbnail,
                    music_id,
                    music_start,
                    music_end
                )
                VALUES (?, ?, ?, ?, ?, ?, ?)
            """, (
                user_id,
                caption,
                dest_name,
                thumb_name,
                music_id if music_id else None,
                music_start,
                music_end
            ))

            reel_id = c.lastrowid

            if music_id:
                c.execute("""
                    INSERT INTO reel_audio
                    (
                        reel_id,
                        music_id,
                        start_time,
                        end_time
                    )
                    VALUES (?, ?, ?, ?)
                """, (
                    reel_id,
                    music_id,
                    music_start,
                    music_end
                ))

            conn.commit()
            conn.close()

            flash("Reel published successfully!", "success")
            return redirect("/reels")

        # --------------------------
        # STORY
        # --------------------------
        elif mode == "story":

            from routes.stories import load_stories, save_stories

            stories = load_stories()

            story_id = max(
                [s.get("id", 0) for s in stories],
                default=0
            ) + 1

            stories.append({
                "id": story_id,
                "user_id": str(user_id),
                "filename": dest_name,
                "timestamp": int(time.time()),
                "viewers": [],
                "likes": [],
                "reactions": {}
            })

            save_stories(stories)

            if music_id:
                c.execute("""
                    INSERT INTO media_audio
                    (
                        media_type,
                        media_id,
                        music_id,
                        start_time,
                        end_time,
                        original_volume,
                        music_volume
                    )
                    VALUES (?, ?, ?, ?, ?, ?, ?)
                """, (
                    "story",
                    story_id,
                    music_id,
                    music_start,
                    music_end,
                    original_volume,
                    music_volume
                ))

            conn.commit()
            conn.close()

            flash("Story uploaded successfully!", "success")
            return redirect("/posts/feed")

        # --------------------------
        # POST
        # --------------------------
        else:

            c.execute("""
                INSERT INTO posts
                (
                    user_id,
                    caption
                )
                VALUES (?, ?)
            """, (
                user_id,
                caption
            ))

            post_id = c.lastrowid

            db_path = "/static/uploads/posts/" + dest_name

            c.execute("""
                INSERT INTO post_images
                (
                    post_id,
                    image_path
                )
                VALUES (?, ?)
            """, (
                post_id,
                db_path
            ))

            if music_id:
                c.execute("""
                    INSERT INTO media_audio
                    (
                        media_type,
                        media_id,
                        music_id,
                        start_time,
                        end_time,
                        original_volume,
                        music_volume
                    )
                    VALUES (?, ?, ?, ?, ?, ?, ?)
                """, (
                    "post",
                    post_id,
                    music_id,
                    music_start,
                    music_end,
                    original_volume,
                    music_volume
                ))

            conn.commit()
            conn.close()

            flash("Post published successfully!", "success")
            return redirect("/posts/feed")

    media_path = request.args.get("media_path", "")
    mode = request.args.get("mode", "post")

    music = None

    music_id = request.args.get("music_id")

    if music_id:
        conn = sqlite3.connect(DB_NAME)
        conn.row_factory = sqlite3.Row

        music = conn.execute(
            "SELECT * FROM music WHERE id=?",
            (music_id,)
        ).fetchone()

        conn.close()

    return render_template(
        "create/publish.html",
        media_path=media_path,
        mode=mode,
        music=music
    )


# ===============================
# 📁 SERVE TEMP FILES
# ===============================
@create_bp.route("/editor_temp/<path:fn>")
def editor_temp(fn):
    return send_from_directory(EDITOR_TEMP_DIR, fn)
