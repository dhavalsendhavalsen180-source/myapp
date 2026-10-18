from flask import Blueprint, render_template, request, redirect, session, flash
import sqlite3
import os
import uuid
from werkzeug.utils import secure_filename

music_bp = Blueprint("music", __name__, url_prefix="/music")

DB_NAME = "database.db"

UPLOAD_FOLDER = os.path.join("static", "music", "uploads")
COVER_FOLDER = os.path.join("static", "music", "covers")

os.makedirs(UPLOAD_FOLDER, exist_ok=True)
os.makedirs(COVER_FOLDER, exist_ok=True)


def get_db():
    conn = sqlite3.connect(DB_NAME)
    conn.row_factory = sqlite3.Row
    return conn


# ==========================
# MUSIC HOME
# ==========================
@music_bp.route("/")
def music_home():

    conn = get_db()

    q = request.args.get("q", "").strip()

    # --------------------------
    # NORMAL MUSIC
    # --------------------------
    if q:

        music = conn.execute("""
            SELECT *
            FROM music
            WHERE blocked=0
              AND (
                    title LIKE ?
                    OR artist LIKE ?
                  )
            ORDER BY id DESC
        """, (
            f"%{q}%",
            f"%{q}%"
        )).fetchall()

    else:

        music = conn.execute("""
            SELECT *
            FROM music
            WHERE blocked=0
            ORDER BY id DESC
        """).fetchall()

    # --------------------------
    # ORIGINAL AUDIO
    # --------------------------
    if q:

        original_audio = conn.execute("""
            SELECT
                oa.id,
                oa.user_id,
                oa.source_type,
                oa.source_media_id,
                oa.audio_file,
                oa.title,
                oa.created_at,
                u.username,
                u.photo
            FROM original_audio oa
            LEFT JOIN users u
                ON oa.user_id = u.id
            WHERE
                oa.title LIKE ?
                OR u.username LIKE ?
            ORDER BY oa.id DESC
        """, (
            f"%{q}%",
            f"%{q}%"
        )).fetchall()

    else:

        original_audio = conn.execute("""
            SELECT
                oa.id,
                oa.user_id,
                oa.source_type,
                oa.source_media_id,
                oa.audio_file,
                oa.title,
                oa.created_at,
                u.username,
                u.photo
            FROM original_audio oa
            LEFT JOIN users u
                ON oa.user_id = u.id
            ORDER BY oa.id DESC
        """).fetchall()

    conn.close()

    return render_template(
        "music/index.html",
        music=music,
        original_audio=original_audio,
        q=q
    )

# ==========================
# MUSIC DETAILS
# ==========================
@music_bp.route("/<int:music_id>")
def music_details(music_id):

    conn = get_db()

    # 🎵 MUSIC
    song = conn.execute("""
        SELECT *
        FROM music
        WHERE id=?
          AND blocked=0
    """, (music_id,)).fetchone()

    if not song:
        conn.close()
        return "Audio not found", 404

    # 💾 CHECK SAVED SONG
    saved = False

    if "user_id" in session:
        saved_row = conn.execute("""
            SELECT id
            FROM music_saves
            WHERE music_id=? AND user_id=?
        """, (music_id, session["user_id"])).fetchone()

        saved = bool(saved_row)

    # 🎬 Is music se bani ALL REELS
    reels = conn.execute("""
        SELECT
            reels.id,
            reels.user_id,
            reels.caption,
            reels.video_path,
            reels.thumbnail,
            reels.likes,
            reels.saves,
            reels.shares,
            reels.comments_count,
            reels.views,
            reels.created_at,
            users.username,
            users.photo
        FROM reels
        INNER JOIN users
            ON reels.user_id = users.id
        WHERE reels.music_id=?
        ORDER BY reels.id DESC
    """, (music_id,)).fetchall()

    # 🖼 Is music se bani ALL POSTS
    # Music posts table me nahi hai.
    # media_audio.media_id = posts.id hota hai.
    posts = conn.execute("""
        SELECT
            posts.id,
            posts.user_id,
            posts.caption,
            posts.created_at,
            users.username,
            users.photo,

            (
                SELECT pi.image_path
                FROM post_images pi
                WHERE pi.post_id = posts.id
                ORDER BY pi.id ASC
                LIMIT 1
            ) AS image_path

        FROM posts

        INNER JOIN users
            ON posts.user_id = users.id

        INNER JOIN media_audio
            ON media_audio.media_type = 'post'
           AND media_audio.media_id = posts.id
           AND media_audio.music_id = ?

        ORDER BY posts.id DESC
    """, (music_id,)).fetchall()

    conn.close()

    return render_template(
        "music/details.html",
        song=song,
        original=None,
        reels=reels,
        posts=posts,
        saved=saved
    )

# ==========================
# ORIGINAL AUDIO DETAILS
# ==========================
@music_bp.route("/original/<int:audio_id>")
def original_audio_details(audio_id):

    conn = get_db()

    # 🎙️ ORIGINAL AUDIO
    audio = conn.execute("""
        SELECT
            oa.id,
            oa.user_id,
            oa.source_type,
            oa.source_media_id,
            oa.audio_file,
            oa.title,
            oa.created_at,
            u.username,
            u.photo
        FROM original_audio oa
        LEFT JOIN users u
            ON oa.user_id = u.id
        WHERE oa.id=?
        LIMIT 1
    """, (audio_id,)).fetchone()

    if not audio:
        conn.close()
        return "Original audio not found", 404

    # 💾 CHECK SAVED ORIGINAL AUDIO
    saved_original = False

    if "user_id" in session:
        saved_row = conn.execute("""
            SELECT id
            FROM original_audio_saves
            WHERE audio_id=? AND user_id=?
        """, (
            audio_id,
            session["user_id"]
        )).fetchone()

        saved_original = bool(saved_row)

    # 🎬 ALL REELS USING THIS ORIGINAL AUDIO
    reels = conn.execute("""
        SELECT
            reels.id,
            reels.user_id,
            reels.caption,
            reels.video_path,
            reels.thumbnail,
            reels.likes,
            reels.saves,
            reels.shares,
            reels.comments_count,
            reels.views,
            reels.created_at,
            users.username,
            users.photo
        FROM reels
        INNER JOIN users
            ON reels.user_id = users.id
        INNER JOIN media_audio
            ON media_audio.media_type = 'reel'
           AND media_audio.media_id = reels.id
           AND media_audio.original_audio_id = ?
        ORDER BY reels.id DESC
    """, (audio_id,)).fetchall()

    # 🖼 ALL POSTS USING THIS ORIGINAL AUDIO
    posts = conn.execute("""
        SELECT
            posts.id,
            posts.user_id,
            posts.caption,
            posts.created_at,
            users.username,
            users.photo,

            (
                SELECT pi.image_path
                FROM post_images pi
                WHERE pi.post_id = posts.id
                ORDER BY pi.id ASC
                LIMIT 1
            ) AS image_path

        FROM posts

        INNER JOIN users
            ON posts.user_id = users.id

        INNER JOIN media_audio
            ON media_audio.media_type = 'post'
           AND media_audio.media_id = posts.id
           AND media_audio.original_audio_id = ?

        ORDER BY posts.id DESC
    """, (audio_id,)).fetchall()

    conn.close()

    return render_template(
        "music/details.html",
        song=None,
        original=audio,
        reels=reels,
        posts=posts,
        saved_original=saved_original
    )

# ==========================
# MUSIC UPLOAD
# ==========================
@music_bp.route("/upload", methods=["GET", "POST"])
def upload_music():

    if "user_id" not in session:
        return redirect("/auth/login")

    if request.method == "POST":

        title = request.form.get("title", "")
        artist = request.form.get("artist", "")

        audio = request.files.get("audio")
        cover = request.files.get("cover")

        if not audio:
            flash("Select audio.")
            return redirect(request.url)

        audio_name = (
            uuid.uuid4().hex
            + "_"
            + secure_filename(audio.filename)
        )

        audio.save(
            os.path.join(
                UPLOAD_FOLDER,
                audio_name
            )
        )

        cover_name = ""

        if cover:

            cover_name = (
                uuid.uuid4().hex
                + "_"
                + secure_filename(cover.filename)
            )

            cover.save(
                os.path.join(
                    COVER_FOLDER,
                    cover_name
                )
            )

        conn = get_db()

        conn.execute("""
            INSERT INTO music
            (
                title,
                artist,
                filename,
                cover,
                uploaded_by
            )
            VALUES
            (?, ?, ?, ?, ?)
        """, (
            title,
            artist,
            audio_name,
            cover_name,
            session["user_id"]
        ))

        conn.commit()
        conn.close()

        flash("Music Uploaded!")

        return redirect("/music")

    return render_template(
        "music/upload.html"
    )


# ==========================
# REPORT AUDIO
# ==========================
@music_bp.route(
    "/report/<int:music_id>",
    methods=["GET", "POST"]
)
def report_audio(music_id):

    if "user_id" not in session:
        return redirect("/auth/login")

    conn = get_db()

    song = conn.execute(
        "SELECT * FROM music WHERE id=?",
        (music_id,)
    ).fetchone()

    if not song:

        conn.close()

        flash("Audio not found.")

        return redirect("/music")

    if request.method == "POST":

        reason = request.form.get(
            "reason",
            ""
        ).strip()

        details = request.form.get(
            "details",
            ""
        ).strip()

        conn.execute("""
            INSERT INTO copyright_reports
            (
                music_id,
                reported_by,
                reason,
                details
            )
            VALUES
            (?, ?, ?, ?)
        """, (
            music_id,
            session["user_id"],
            reason,
            details
        ))

        conn.execute("""
            UPDATE music
            SET report_count = report_count + 1
            WHERE id=?
        """, (music_id,))

        conn.commit()
        conn.close()

        flash(
            "Report submitted successfully."
        )

        return redirect(
            f"/music/{music_id}"
        )

    conn.close()

    return render_template(
        "music/report.html",
        song=song
    )


# ==========================
# USE NORMAL MUSIC
# ==========================
@music_bp.route("/use/<int:music_id>")
def use_audio(music_id):

    if "user_id" not in session:
        return redirect("/auth/login")

    conn = get_db()

    song = conn.execute("""
        SELECT *
        FROM music
        WHERE id=? AND blocked=0
    """, (music_id,)).fetchone()

    conn.close()

    if not song:

        flash(
            "Audio not found.",
            "error"
        )

        return redirect("/music")

    media_path = request.args.get(
        "media_path",
        ""
    )

    mode = request.args.get(
        "mode",
        "reel"
    )

    return redirect(
        f"/create/editor"
        f"?mode={mode}"
        f"&media_path={media_path}"
        f"&music_id={music_id}"
    )


# ==========================
# USE ORIGINAL AUDIO
# ==========================
@music_bp.route("/use-original/<int:audio_id>")
def use_original_audio(audio_id):

    if "user_id" not in session:
        return redirect("/auth/login")

    conn = get_db()

    audio = conn.execute("""
        SELECT *
        FROM original_audio
        WHERE id=?
    """, (audio_id,)).fetchone()

    conn.close()

    if not audio:
        flash(
            "Original audio not found.",
            "error"
        )
        return redirect("/music")

    # Media jis Reel/Post se audio aaya hai
    media_path = request.args.get("media_path", "").strip()

    mode = request.args.get("mode", "reel").strip()

    # Editor par selected original audio ke saath bhejo
    return redirect(
        f"/create"
        f"?mode={mode}"
        f"&original_audio_id={audio_id}"
    )

# ==========================
# SAVE / UNSAVE MUSIC
# ==========================
@music_bp.route("/save_toggle/<int:music_id>", methods=["POST"])
def save_music_toggle(music_id):

    if "user_id" not in session:
        return redirect("/auth/login")

    user_id = session["user_id"]

    conn = get_db()

    song = conn.execute("""
        SELECT id
        FROM music
        WHERE id=? AND blocked=0
    """, (music_id,)).fetchone()

    if not song:
        conn.close()
        flash("Audio not found.", "error")
        return redirect("/music")

    saved = conn.execute("""
        SELECT id
        FROM music_saves
        WHERE music_id=? AND user_id=?
    """, (music_id, user_id)).fetchone()

    if saved:

        conn.execute("""
            DELETE FROM music_saves
            WHERE music_id=? AND user_id=?
        """, (music_id, user_id))

        flash("Song removed from Saved Songs.", "success")

    else:

        conn.execute("""
            INSERT INTO music_saves
            (music_id, user_id)
            VALUES (?, ?)
        """, (music_id, user_id))

        flash("Song saved successfully.", "success")

    conn.commit()
    conn.close()

    return redirect(request.referrer or "/music")


# ==========================
# SAVE / UNSAVE ORIGINAL AUDIO
# ==========================
@music_bp.route("/save_original_toggle/<int:audio_id>", methods=["POST"])
def save_original_audio_toggle(audio_id):

    if "user_id" not in session:
        return redirect("/auth/login")

    user_id = session["user_id"]

    conn = get_db()

    audio = conn.execute("""
        SELECT id
        FROM original_audio
        WHERE id=?
    """, (audio_id,)).fetchone()

    if not audio:
        conn.close()
        flash("Original audio not found.", "error")
        return redirect("/music")

    saved = conn.execute("""
        SELECT id
        FROM original_audio_saves
        WHERE audio_id=? AND user_id=?
    """, (
        audio_id,
        user_id
    )).fetchone()

    if saved:

        conn.execute("""
            DELETE FROM original_audio_saves
            WHERE audio_id=? AND user_id=?
        """, (
            audio_id,
            user_id
        ))

        flash("Original audio removed from Saved.", "success")

    else:

        conn.execute("""
            INSERT INTO original_audio_saves
            (audio_id, user_id)
            VALUES (?, ?)
        """, (
            audio_id,
            user_id
        ))

        flash("Original audio saved successfully.", "success")

    conn.commit()
    conn.close()

    return redirect(request.referrer or "/music")
