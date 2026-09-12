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

    song = conn.execute("""
        SELECT *
        FROM music
        WHERE id=?
    """, (music_id,)).fetchone()

    reels = conn.execute("""
        SELECT
            reels.*
        FROM reels
        INNER JOIN reel_audio
            ON reels.id = reel_audio.reel_id
        WHERE reel_audio.music_id = ?
        ORDER BY reels.id DESC
    """, (music_id,)).fetchall()

    conn.close()

    if not song:
        return "Audio not found", 404

    return render_template(
        "music/details.html",
        song=song,
        original=None,
        reels=reels
    )


# ==========================
# ORIGINAL AUDIO DETAILS
# ==========================
@music_bp.route("/original/<int:audio_id>")
def original_audio_details(audio_id):

    conn = get_db()

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

    conn.close()

    if not audio:
        return "Original audio not found", 404

    return render_template(
        "music/details.html",
        song=None,
        original=audio,
        reels=[]
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
        f"/create/editor"
        f"?mode={mode}"
        f"&media_path={media_path}"
        f"&original_audio_id={audio_id}"
    )
