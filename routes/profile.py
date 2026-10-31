from flask import Blueprint, render_template, request, redirect, session, url_for, flash
import sqlite3
import os
import calendar
import json
from datetime import datetime
from werkzeug.utils import secure_filename
from werkzeug.security import check_password_hash, generate_password_hash
from routes.stories import load_stories_for_feed

profile_bp = Blueprint("profile_bp", __name__, url_prefix="/profile")

DB_NAME = "database.db"
UPLOAD_FOLDER = "static/profile"
ALLOWED_EXT = {"png", "jpg", "jpeg"}

os.makedirs(UPLOAD_FOLDER, exist_ok=True)


def allowed_file(filename):
    return "." in filename and filename.rsplit(".", 1)[1].lower() in ALLOWED_EXT


# ------------------ OWN PROFILE ------------------ #
@profile_bp.route("/")
def my_profile():
    if "user_id" not in session:
        return redirect("/auth/login")

    return redirect(f"/profile/{session['user_id']}")


# ------------------ VIEW USER PROFILE ------------------ #
@profile_bp.route("/<int:user_id>")
def profile(user_id):

    conn = sqlite3.connect(DB_NAME)
    conn.row_factory = sqlite3.Row
    c = conn.cursor()

    # USER
    c.execute("""
        SELECT
            id,
            username,
            bio,
            photo,
            is_private,
            COALESCE(suspended, 0) AS suspended,
            COALESCE(banned, 0) AS banned,
            deletion_requested_at
        FROM users
        WHERE id=?
    """, (user_id,))

    u = c.fetchone()

    if not u or u["suspended"] or u["banned"] or u["deletion_requested_at"]:
        conn.close()
        return "User not found", 404

    profile_data = {
        "id": u["id"],
        "username": u["username"],
        "bio": u["bio"] or "",
        "photo": u["photo"] if u["photo"] else "/static/default_dp.png",
        "is_private": u["is_private"] if "is_private" in u.keys() else 0,
    }

    # CURRENT USER
    current = session.get("user_id")
    # -------- STORY STATUS --------
    stories = load_stories_for_feed()

    has_story = False
    story_seen = True

    for s in stories:

        if str(s["user_id"]) != str(user_id):
            continue

        has_story = True

        viewers = [str(v) for v in s.get("viewers", [])]

        if not current or str(current) not in viewers:
            story_seen = False
            break

    if not has_story:
        story_seen = False

    # FOLLOW CHECK
    is_following = False

    if current and current != user_id:
        c.execute("""
            SELECT 1
            FROM follows
            WHERE follower_id=? AND following_id=?
        """, (current, user_id))

        is_following = c.fetchone() is not None
    # -------- FOLLOW REQUEST CHECK --------
    follow_requested = False

    if current and current != user_id:
        c.execute("""
            SELECT 1
            FROM follow_requests
            WHERE sender_id=? AND receiver_id=?
        """, (current, user_id))

        follow_requested = c.fetchone() is not None

    # PRIVATE ACCOUNT CHECK
    can_view = True

    if profile_data["is_private"] == 1:
        if current != user_id and not is_following:
            can_view = False

# CHAT BUTTON PERMISSION
# Public account -> Chat allowed
# Private account -> Chat only if already following
    can_chat = False

    if current and current != user_id:

        if profile_data["is_private"] == 0:
        # PUBLIC ACCOUNT
            can_chat = True

        elif is_following:
        # PRIVATE ACCOUNT + FOLLOW ACCEPTED
            can_chat = True

    # POSTS
    posts = []

    if can_view:
        c.execute("""
            SELECT id
            FROM posts
            WHERE user_id=?
            ORDER BY id DESC
        """, (user_id,))

        post_ids = c.fetchall()

        for p in post_ids:
            c.execute("""
                SELECT image_path
                FROM post_images
                WHERE post_id=?
                LIMIT 1
            """, (p["id"],))

            img = c.fetchone()

            posts.append({
                "id": p["id"],
                "image": img["image_path"] if img else None,
            })

    # REELS
    reels_data = []

    if can_view:
        c.execute("""
            SELECT id, video_path, thumbnail
            FROM reels
            WHERE user_id=?
            ORDER BY id DESC
        """, (user_id,))

        reels_rows = c.fetchall()

        for r in reels_rows:
            reels_data.append({
                "id": r["id"],
                "video": "/static/uploads/reels/" + r["video_path"],
                "thumbnail": r["thumbnail"],
            })

    # FOLLOW COUNTS
    c.execute("""
        SELECT COUNT(*)
        FROM follows
        WHERE following_id=?
    """, (user_id,))

    followers = c.fetchone()[0]

    c.execute("""
        SELECT COUNT(*)
        FROM follows
        WHERE follower_id=?
    """, (user_id,))

    following = c.fetchone()[0]

    conn.close()

    return render_template(
        "profile.html",
        profile=profile_data,
        posts=posts,
        reels=reels_data,
        followers=followers,
        following=following,
        is_following=is_following,
        follow_requested=follow_requested,
        current_user=current,
        is_owner=(current is not None and str(current) == str(user_id)),
        can_view=can_view,
        can_chat=can_chat,
        has_story=has_story,
        story_seen=story_seen

    )

# ------------------ EDIT PROFILE ------------------ #
@profile_bp.route("/edit", methods=["POST"])
@profile_bp.route("/edit", methods=["POST"])
def edit_profile():

    if "user_id" not in session:
        return redirect("/auth/login")

    uid = session["user_id"]

    username = request.form.get("username", "").strip()
    import re

    if not re.fullmatch(r"[A-Za-z0-9._]+", username):
        conn = sqlite3.connect(DB_NAME)
        conn.close()
        return redirect(f"/profile/{uid}?error=invalid_username")
    bio = request.form.get("bio", "").strip()
    photo = request.files.get("photo")

    conn = sqlite3.connect(DB_NAME)
    c = conn.cursor()

    # CHECK DUPLICATE USERNAME
    c.execute("SELECT id FROM users WHERE username=? AND id!=?", (username, uid))
    if c.fetchone():
        conn.close()
        return redirect(f"/profile/{uid}?error=username_taken")

    if photo and photo.filename and allowed_file(photo.filename):
        ext = photo.filename.rsplit(".", 1)[1].lower()
        filename = secure_filename(f"user_{uid}.{ext}")
        save_path = os.path.join(UPLOAD_FOLDER, filename)
        photo.save(save_path)
        photo_url = "/" + save_path.replace("\\", "/")
        c.execute("UPDATE users SET photo=? WHERE id=?", (photo_url, uid))

    c.execute("UPDATE users SET username=?, bio=? WHERE id=?", (username, bio, uid))

    conn.commit()
    conn.close()

    return redirect(f"/profile/{uid}")

# ------------------ FOLLOWERS ------------------ #
@profile_bp.route("/<int:user_id>/followers")
def followers_list(user_id):

    conn = sqlite3.connect(DB_NAME)
    conn.row_factory = sqlite3.Row
    c = conn.cursor()

    c.execute("""
        SELECT id, username, photo,
               COALESCE(suspended, 0) AS suspended,
               COALESCE(banned, 0) AS banned,
               deletion_requested_at
        FROM users
        WHERE id=?
    """, (user_id,))
    u = c.fetchone()

    if not u or u["suspended"] or u["banned"] or u["deletion_requested_at"]:
        conn.close()
        return "User not found", 404

    c.execute("""
        SELECT u.id, u.username, u.photo
        FROM follows f
        JOIN users u ON f.follower_id = u.id
        WHERE f.following_id=?
    """, (user_id,))

    followers = c.fetchall()
    conn.close()

    return render_template("followers.html", followers=followers, user=u)


# ------------------ FOLLOWING ------------------ #
@profile_bp.route("/<int:user_id>/following")
def following_list(user_id):

    conn = sqlite3.connect(DB_NAME)
    conn.row_factory = sqlite3.Row
    c = conn.cursor()

    c.execute("""
        SELECT id, username, photo,
               COALESCE(suspended, 0) AS suspended,
               COALESCE(banned, 0) AS banned,
               deletion_requested_at
        FROM users
        WHERE id=?
    """, (user_id,))

    u = c.fetchone()

    if not u or u["suspended"] or u["banned"] or u["deletion_requested_at"]:
        conn.close()
        return "User not found", 404

    c.execute("""
        SELECT u.id, u.username, u.photo
        FROM follows f
        JOIN users u ON f.following_id = u.id
        WHERE f.follower_id=?
    """, (user_id,))

    following = c.fetchall()
    conn.close()

    return render_template("following.html", following=following, user=u)


# ------------------ SETTINGS ------------------ #
@profile_bp.route("/settings")
def settings_page():
    if "user_id" not in session:
        return redirect("/auth/login")

    return render_template("settings.html")


# ------------------ SAVED POSTS ------------------ #
# ------------------ SAVED ------------------ #
@profile_bp.route("/saved")
def saved_page():

    if "user_id" not in session:
        return redirect("/auth/login")

    uid = session["user_id"]

    conn = sqlite3.connect(DB_NAME)
    conn.row_factory = sqlite3.Row
    c = conn.cursor()

    # SAVED POSTS
    c.execute("""
        SELECT posts.id, posts.caption
        FROM post_saves
        JOIN posts
            ON post_saves.post_id = posts.id
        JOIN users
            ON posts.user_id = users.id
        WHERE post_saves.user_id = ?
          AND COALESCE(users.suspended, 0) = 0
          AND COALESCE(users.banned, 0) = 0
        ORDER BY posts.id DESC
    """, (uid,))

    rows = c.fetchall()

    saved_posts = []

    for r in rows:
        c.execute(
            "SELECT image_path FROM post_images WHERE post_id=? LIMIT 1",
            (r["id"],)
        )

        img = c.fetchone()

        saved_posts.append({
            "id": r["id"],
            "caption": r["caption"],
            "image": img["image_path"] if img else None
        })

    # SAVED REELS — hide suspended/banned owners
    c.execute("""
        SELECT r.*
        FROM reel_saves rs
        JOIN reels r
            ON r.id = rs.reel_id
        JOIN users u
            ON r.user_id = u.id
        WHERE rs.user_id = ?
          AND COALESCE(u.suspended, 0) = 0
          AND COALESCE(u.banned, 0) = 0
        ORDER BY rs.id DESC
    """, (uid,))

    saved_reels = c.fetchall()

    # SAVED MUSIC / SONGS
    c.execute("""
        SELECT
            m.id,
            m.title,
            m.artist,
            m.filename,
            m.cover,
            m.duration
        FROM music_saves ms
        JOIN music m ON m.id = ms.music_id
        WHERE ms.user_id=? AND m.blocked=0
        ORDER BY ms.id DESC
    """, (uid,))

    saved_music = c.fetchall()

    # SAVED ORIGINAL AUDIO
    c.execute("""
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
        FROM original_audio_saves oas
        JOIN original_audio oa
            ON oa.id = oas.audio_id
        LEFT JOIN users u
            ON oa.user_id = u.id
        WHERE oas.user_id=?
        ORDER BY oas.id DESC
    """, (uid,))

    saved_original_audio = c.fetchall()

    conn.close()

    return render_template(
        "saved.html",
        saved_posts=saved_posts,
        saved_reels=saved_reels,
        saved_music=saved_music,
        saved_original_audio=saved_original_audio
    )

########################################
@profile_bp.route("/reels")
def full_reels():

    start = int(request.args.get("start", 0))
    current = session.get("user_id")

    conn = sqlite3.connect(DB_NAME)
    conn.row_factory = sqlite3.Row
    c = conn.cursor()

    # USER (for username display)
    profile = None
    if current:
        c.execute("SELECT id, username, photo FROM users WHERE id=?", (current,))
        profile = c.fetchone()

    # REELS LOAD
    c.execute("SELECT * FROM reels ORDER BY id DESC")
    rows = c.fetchall()

    reels = []
    for r in rows:
        reels.append({
            "video": "/static/uploads/reels/" + r["video_path"],
                "thumbnail": r["thumbnail"],
            "caption": r["caption"] if "caption" in r.keys() else ""
        })

    conn.close()

    return redirect(f"/reels?start={start}")
    return render_template(
        "reels.html",
        reels=reels,
        start=start,
        profile=profile   # ✅ FIX
    )


# ------------------ TOGGLE PRIVATE ACCOUNT ------------------ #
@profile_bp.route("/toggle_private", methods=["POST"])
def toggle_private():

    if "user_id" not in session:
        return redirect("/auth/login")

    uid = session["user_id"]

    conn = sqlite3.connect(DB_NAME)
    c = conn.cursor()

    # current value
    c.execute("SELECT is_private FROM users WHERE id=?", (uid,))
    row = c.fetchone()

    current = row[0] if row else 0
    new_value = 0 if current == 1 else 1

    c.execute(
        "UPDATE users SET is_private=? WHERE id=?",
        (new_value, uid)
    )

    conn.commit()
    conn.close()

    return redirect(f"/profile/{uid}")

# ------------------ ACCOUNT PRIVACY ------------------ #
@profile_bp.route("/privacy")
def privacy_page():

    if "user_id" not in session:
        return redirect("/auth/login")

    uid = session["user_id"]

    conn = sqlite3.connect(DB_NAME)
    conn.row_factory = sqlite3.Row
    c = conn.cursor()

    c.execute(
        "SELECT is_private FROM users WHERE id=?",
        (uid,)
    )

    profile = c.fetchone()

    conn.close()

    return render_template(
        "privacy.html",
        profile=profile
    )
# ------------------ ACCOUNT CENTER ------------------ #
@profile_bp.route("/account_center")
def account_center():

    if "user_id" not in session:
        return redirect("/auth/login")

    uid = session["user_id"]

    conn = sqlite3.connect(DB_NAME)
    conn.row_factory = sqlite3.Row
    c = conn.cursor()

    c.execute("""
        SELECT id, username, email, phone
        FROM users
        WHERE id=?
    """, (uid,))

    user = c.fetchone()

    conn.close()

    if not user:
        session.clear()
        return redirect("/auth/login")

    return render_template(
        "account_center.html",
        user=user
    )


# ------------------ CHANGE PASSWORD PAGE ------------------ #
@profile_bp.route("/change-password", methods=["GET", "POST"])
def change_password():

    if "user_id" not in session:
        return redirect("/auth/login")

    uid = session["user_id"]

    if request.method == "POST":

        current_password = request.form.get(
            "current_password",
            ""
        ).strip()

        new_password = request.form.get(
            "new_password",
            ""
        ).strip()

        confirm_password = request.form.get(
            "confirm_password",
            ""
        ).strip()

        if not current_password:
            flash("Please enter your current password.", "error")
            return redirect(url_for("profile_bp.change_password"))

        if not new_password:
            flash("Please enter a new password.", "error")
            return redirect(url_for("profile_bp.change_password"))

        if len(new_password) < 8:
            flash(
                "New password must be at least 8 characters.",
                "error"
            )
            return redirect(url_for("profile_bp.change_password"))

        if new_password != confirm_password:
            flash(
                "New passwords do not match.",
                "error"
            )
            return redirect(url_for("profile_bp.change_password"))

        conn = sqlite3.connect(DB_NAME)
        c = conn.cursor()

        c.execute("""
            SELECT password
            FROM users
            WHERE id=?
        """, (uid,))

        row = c.fetchone()

        if not row:
            conn.close()

            session.clear()

            flash("Account not found. Please login again.", "error")

            return redirect("/auth/login")

        stored_password = row[0]

        if not check_password_hash(
            stored_password,
            current_password
        ):

            conn.close()

            flash(
                "Current password is incorrect.",
                "error"
            )

            return redirect(
                url_for("profile_bp.change_password")
            )

        new_hashed_password = generate_password_hash(
            new_password
        )

        c.execute("""
            UPDATE users
            SET password=?
            WHERE id=?
        """, (
            new_hashed_password,
            uid
        ))

        conn.commit()
        conn.close()

        flash(
            "Password changed successfully.",
            "success"
        )

        return redirect(
            url_for("profile_bp.account_center")
        )

    return render_template("change_password.html")

# ------------------ REQUEST ACCOUNT DELETION ------------------ #
@profile_bp.route("/request-account-deletion", methods=["POST"])
def request_account_deletion():
    if "user_id" not in session:
        return redirect("/auth/login")

    uid = session["user_id"]
    current_password = request.form.get("current_password", "")

    conn = sqlite3.connect(DB_NAME)
    conn.row_factory = sqlite3.Row

    try:
        row = conn.execute("""
            SELECT password, suspended, banned, deletion_requested_at
            FROM users
            WHERE id = ?
        """, (uid,)).fetchone()

        if not row:
            session.clear()
            return redirect("/auth/login")

        if row["banned"] or row["suspended"]:
            flash("Restricted accounts cannot request deletion here.", "error")
            return redirect(url_for("profile_bp.account_center"))

        if row["deletion_requested_at"]:
            flash("Account deletion is already pending.", "error")
            return redirect(url_for("account_guard.account_status"))

        if not check_password_hash(row["password"], current_password):
            flash("Current password is incorrect.", "error")
            return redirect(url_for("profile_bp.account_center"))

        request_time = datetime.now()

        requested_at = request_time.strftime("%Y-%m-%d %H:%M:%S")

        target_month = request_time.month - 1 + 6
        expiry_year = request_time.year + target_month // 12
        expiry_month = target_month % 12 + 1

        expiry_day = min(
            request_time.day,
            calendar.monthrange(expiry_year, expiry_month)[1]
        )

        expiry_time = request_time.replace(
            year=expiry_year,
            month=expiry_month,
            day=expiry_day
        )

        deletion_expires_at = expiry_time.strftime("%Y-%m-%d %H:%M:%S")

        result = conn.execute("""
            UPDATE users
            SET deletion_requested_at = ?,
                deletion_expires_at = ?
            WHERE id = ?
              AND deletion_requested_at IS NULL
              AND COALESCE(suspended, 0) = 0
              AND COALESCE(banned, 0) = 0
        """, (requested_at, deletion_expires_at, uid))

        conn.commit()

        if result.rowcount != 1:
            flash("Deletion request could not be saved. Please try again.", "error")
            return redirect(url_for("profile_bp.account_center"))

    except Exception:
        conn.rollback()
        raise
    finally:
        conn.close()

    return redirect(url_for("account_guard.account_status"))

# InsChat: limited account-deletion cleanup
# InsChat: limited account-deletion cleanup
# Scope: posts, post images, reels, reel-related rows,
# follows and follow requests only.
def cleanup_expired_posts_reels_follows(
    db_path="database.db",
    dry_run=True,
):
    """
    Expired account cleanup.
    dry_run=True  -> sirf report, koi changes nahi.
    dry_run=False -> database, JSON aur associated files clean.
    """

    now = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
    app_root = os.path.abspath(os.path.join(os.path.dirname(__file__), ".."))

    result = {
        "mode": "DRY RUN" if dry_run else "EXECUTE",
        "expired_accounts_processed": 0,
        "posts": 0,
        "post_images": 0,
        "likes": 0,
        "comments": 0,
        "comment_likes": 0,
        "post_saves": 0,
        "reels": 0,
        "reel_related_rows": 0,
        "follows": 0,
        "follow_requests": 0,
        "notifications": 0,
        "stories": 0,
        "story_replies": 0,
        "messages": 0,
        "message_receipts": 0,
        "message_screenshots": 0,
        "calls": 0,
        "chats": 0,
        "reports": 0,
        "files_removed": 0,
        "users_removed": 0,
    }

    story_json_path = os.path.join(app_root, "data", "stories.json")
    replies_json_path = os.path.join(app_root, "data", "story_replies.json")

    def load_json(path):
        if not os.path.isfile(path):
            return []
        with open(path, "r", encoding="utf-8") as f:
            data = json.load(f)
        return data if isinstance(data, list) else []

    def save_json_atomic(path, data):
        os.makedirs(os.path.dirname(path), exist_ok=True)
        temp_path = path + ".cleanup_tmp"
        with open(temp_path, "w", encoding="utf-8") as f:
            json.dump(data, f, ensure_ascii=False, indent=2)
            f.flush()
            os.fsync(f.fileno())
        os.replace(temp_path, path)

    def table_exists(con, table):
        return con.execute(
            "SELECT 1 FROM sqlite_master WHERE type='table' AND name=?",
            (table,),
        ).fetchone() is not None

    def columns(con, table):
        if not table_exists(con, table):
            return set()
        return {
            row[1]
            for row in con.execute(f'PRAGMA table_info("{table}")')
        }

    def count_where(con, table, where, params=()):
        if not table_exists(con, table):
            return 0
        return con.execute(
            f'SELECT COUNT(*) FROM "{table}" WHERE {where}', params
        ).fetchone()[0]

    def delete_where(con, table, where, params=()):
        if not table_exists(con, table):
            return 0
        cur = con.execute(
            f'DELETE FROM "{table}" WHERE {where}', params
        )
        return max(cur.rowcount, 0)

    def add_file_path(paths, value):
        if not isinstance(value, str) or not value.strip():
            return
        value = value.strip()

        # Sirf app ke andar ki files allow hain.
        candidate = os.path.abspath(
            value if os.path.isabs(value) else os.path.join(app_root, value)
        )
        try:
            if os.path.commonpath([app_root, candidate]) == app_root:
                paths.add(candidate)
        except ValueError:
            pass

    con = sqlite3.connect(db_path)
    con.row_factory = sqlite3.Row
    files_to_remove = set()

    try:
        con.execute("PRAGMA foreign_keys = ON")

        expired_users = con.execute("""
            SELECT id, username, photo
            FROM users
            WHERE deletion_requested_at IS NOT NULL
              AND deletion_expires_at IS NOT NULL
              AND deletion_expires_at <= ?
              AND COALESCE(suspended, 0) = 0
              AND COALESCE(banned, 0) = 0
              AND id != 1
        """, (now,)).fetchall()

        # JSON records pehle memory mein read honge.
        all_stories = load_json(story_json_path)
        all_replies = load_json(replies_json_path)

        stories_to_keep = list(all_stories)
        replies_to_keep = list(all_replies)

        result["expired_accounts_processed"] = len(expired_users)

        if not dry_run:
            con.execute("BEGIN IMMEDIATE")

        for user in expired_users:
            uid = user["id"]
            username = str(user["username"])
            user_keys = {str(uid), username}

            add_file_path(files_to_remove, user["photo"])

            # Owned post/reel IDs.
            post_ids = [
                r[0] for r in con.execute(
                    "SELECT id FROM posts WHERE user_id=?", (uid,)
                ).fetchall()
            ]
            reel_ids = [
                r[0] for r in con.execute(
                    "SELECT id FROM reels WHERE user_id=?", (uid,)
                ).fetchall()
            ]

            post_set = set(post_ids)
            reel_set = set(reel_ids)

            # Post media files.
            if post_ids and table_exists(con, "post_images"):
                marks = ",".join("?" for _ in post_ids)
                for r in con.execute(
                    f"SELECT image_path FROM post_images WHERE post_id IN ({marks})",
                    post_ids,
                ):
                    add_file_path(files_to_remove, r[0])

            # Reel video/thumbnail files.
            if reel_ids and table_exists(con, "reels"):
                marks = ",".join("?" for _ in reel_ids)
                for r in con.execute(
                    f"SELECT video_path, thumbnail FROM reels WHERE id IN ({marks})",
                    reel_ids,
                ):
                    add_file_path(files_to_remove, r[0])
                    add_file_path(files_to_remove, r[1])

            # Comments on owned posts OR comments written by this user.
            comment_ids = []
            if table_exists(con, "comments"):
                comment_ids = [
                    r[0] for r in con.execute("""
                        SELECT id FROM comments
                        WHERE user_id=? OR post_id IN (
                            SELECT id FROM posts WHERE user_id=?
                        )
                    """, (uid, uid)).fetchall()
                ]

            # Story JSON records and their media.
            owned_story_ids = set()
            for story in all_stories:
                story_uid = str(story.get("user_id", ""))
                if story_uid in user_keys:
                    owned_story_ids.add(str(story.get("id", "")))

                    filename = story.get("filename")
                    if filename:
                        add_file_path(files_to_remove, os.path.join("static", "stories", filename))
                        add_file_path(files_to_remove, os.path.join("static", "uploads", "stories", filename))

                    add_file_path(files_to_remove, story.get("media_path"))
                    add_file_path(files_to_remove, story.get("story_path"))

            stories_to_keep = [
                s for s in stories_to_keep
                if str(s.get("user_id", "")) not in user_keys
            ]

            # Replies: remove replies sent by this user, addressed to this user,
            # or attached to a story owned by this user.
            def reply_belongs_to_user(reply):
                sender = str(reply.get("from", ""))
                recipient = str(reply.get("to_user", ""))
                story_id = str(reply.get("story_id", ""))
                return (
                    sender in user_keys
                    or recipient in user_keys
                    or story_id in owned_story_ids
                )

            replies_to_keep = [
                r for r in replies_to_keep if not reply_belongs_to_user(r)
            ]

            result["stories"] += sum(
                1 for s in all_stories
                if str(s.get("user_id", "")) in user_keys
            )
            result["story_replies"] += sum(
                1 for r in all_replies if reply_belongs_to_user(r)
            )

            # Delete owned posts' related rows and user's comments on others' posts.
            if post_ids:
                marks = ",".join("?" for _ in post_ids)
                result["post_images"] += count_where(
                    con, "post_images", f"post_id IN ({marks})", post_ids
                )
                result["likes"] += count_where(
                    con, "likes", f"post_id IN ({marks})", post_ids
                )
                result["post_saves"] += count_where(
                    con, "post_saves", f"post_id IN ({marks})", post_ids
                )

            result["comments"] += count_where(
                con, "comments",
                "user_id=? OR post_id IN (SELECT id FROM posts WHERE user_id=?)",
                (uid, uid),
            )

            if comment_ids:
                marks = ",".join("?" for _ in comment_ids)
                result["comment_likes"] += count_where(
                    con, "comment_likes", f"comment_id IN ({marks})", comment_ids
                )

            if reel_ids:
                marks = ",".join("?" for _ in reel_ids)
                for table in (
                    "reel_likes", "reel_comments", "reel_saves",
                    "reel_shares", "reel_views", "reel_audio",
                ):
                    if table_exists(con, table) and "reel_id" in columns(con, table):
                        result["reel_related_rows"] += count_where(
                            con, table, f"reel_id IN ({marks})", reel_ids
                        )

            # Count likes on reel comments that will be deleted.
            reel_comment_ids = []
            if table_exists(con, "reel_comments"):
                reel_comment_ids = [
                    row[0] for row in con.execute(
                        "SELECT id FROM reel_comments WHERE user_id=? "
                        "OR reel_id IN (SELECT id FROM reels WHERE user_id=?)",
                        (uid, uid),
                    ).fetchall()
                ]

            if reel_comment_ids and table_exists(con, "reel_comment_likes"):
                marks = ",".join("?" for _ in reel_comment_ids)
                result["reel_related_rows"] += count_where(
                    con, "reel_comment_likes",
                    f"comment_id IN ({marks})", reel_comment_ids
                )

            result["follows"] += count_where(
                con, "follows", "follower_id=? OR following_id=?", (uid, uid)
            )
            result["follow_requests"] += count_where(
                con, "follow_requests", "sender_id=? OR receiver_id=?", (uid, uid)
            )
            result["notifications"] += count_where(
                con, "notifications", "user_id=? OR actor_id=?", (uid, uid)
            )
            result["reports"] += count_where(
                con, "reports", "reporter_id=? OR owner_id=?", (uid, uid)
            )

            # Both sides of this user's chat history are removed.
            # chats.user1/user2 may store username or ID as text.
            chat_ids = [
                r[0] for r in con.execute("""
                    SELECT id FROM chats
                    WHERE CAST(user1 AS TEXT) IN (?,?)
                       OR CAST(user2 AS TEXT) IN (?,?)
                """, (str(uid), username, str(uid), username)).fetchall()
            ]

            if chat_ids:
                marks = ",".join("?" for _ in chat_ids)

                for r in con.execute(
                    f"SELECT attachment FROM messages WHERE chat_id IN ({marks})",
                    chat_ids,
                ) if table_exists(con, "messages") else []:
                    add_file_path(files_to_remove, r[0])

                result["messages"] += count_where(
                    con, "messages", f"chat_id IN ({marks})", chat_ids
                )
                result["calls"] += count_where(
                    con, "calls", f"chat_id IN ({marks})", chat_ids
                )
                result["chats"] += len(chat_ids)

                message_ids = [
                    r[0] for r in con.execute(
                        f"SELECT id FROM messages WHERE chat_id IN ({marks})",
                        chat_ids,
                    ).fetchall()
                ] if table_exists(con, "messages") else []

                if message_ids:
                    mm = ",".join("?" for _ in message_ids)
                    result["message_receipts"] += count_where(
                        con, "message_receipts", f"message_id IN ({mm})", message_ids
                    )
                    result["message_screenshots"] += count_where(
                        con, "message_screenshots", f"message_id IN ({mm})", message_ids
                    )

            result["posts"] += len(post_ids)
            result["reels"] += len(reel_ids)

            if not dry_run:
                # Remove dependent rows before parent rows.
                if post_ids:
                    marks = ",".join("?" for _ in post_ids)
                    delete_where(con, "post_images", f"post_id IN ({marks})", post_ids)
                    delete_where(con, "likes", f"post_id IN ({marks})", post_ids)
                    delete_where(con, "post_saves", f"post_id IN ({marks})", post_ids)

                if comment_ids:
                    marks = ",".join("?" for _ in comment_ids)
                    delete_where(con, "comment_likes", f"comment_id IN ({marks})", comment_ids)

                delete_where(
                    con, "comments",
                    "user_id=? OR post_id IN (SELECT id FROM posts WHERE user_id=?)",
                    (uid, uid),
                )

                if reel_comment_ids and table_exists(con, "reel_comment_likes"):
                    marks = ",".join("?" for _ in reel_comment_ids)
                    delete_where(
                        con, "reel_comment_likes",
                        f"comment_id IN ({marks})", reel_comment_ids
                    )

                if reel_ids:
                    marks = ",".join("?" for _ in reel_ids)
                    for table in (
                        "reel_likes", "reel_comments", "reel_saves",
                        "reel_shares", "reel_views", "reel_audio",
                    ):
                        if table_exists(con, table) and "reel_id" in columns(con, table):
                            delete_where(con, table, f"reel_id IN ({marks})", reel_ids)

                delete_where(con, "follows", "follower_id=? OR following_id=?", (uid, uid))
                delete_where(con, "follow_requests", "sender_id=? OR receiver_id=?", (uid, uid))
                delete_where(con, "notifications", "user_id=? OR actor_id=?", (uid, uid))
                delete_where(con, "reports", "reporter_id=? OR owner_id=?", (uid, uid))

                if chat_ids:
                    marks = ",".join("?" for _ in chat_ids)
                    message_ids = [
                        r[0] for r in con.execute(
                            f"SELECT id FROM messages WHERE chat_id IN ({marks})",
                            chat_ids,
                        ).fetchall()
                    ] if table_exists(con, "messages") else []

                    if message_ids:
                        mm = ",".join("?" for _ in message_ids)
                        delete_where(con, "message_receipts", f"message_id IN ({mm})", message_ids)
                        delete_where(con, "message_screenshots", f"message_id IN ({mm})", message_ids)

                    delete_where(con, "messages", f"chat_id IN ({marks})", chat_ids)
                    delete_where(con, "calls", f"chat_id IN ({marks})", chat_ids)
                    delete_where(con, "chats", f"id IN ({marks})", chat_ids)

                # Remove rows where this user is the actor/commenter/saver.
                delete_where(con, "comment_likes", "user_id=?", (uid,))
                delete_where(con, "reel_comment_likes", "user_id=?", (uid,))
                delete_where(con, "reel_likes", "user_id=?", (uid,))
                delete_where(con, "reel_comments", "user_id=?", (uid,))
                delete_where(con, "reel_saves", "user_id=?", (uid,))
                delete_where(con, "reel_views", "user_id=?", (uid,))
                delete_where(con, "reel_shares", "sender_id=? OR receiver_id=?", (uid, uid))
                delete_where(con, "music_saves", "user_id=?", (uid,))
                delete_where(con, "original_audio_saves", "user_id=?", (uid,))
                delete_where(con, "post_saves", "user_id=?", (uid,))
                delete_where(con, "likes", "user_id=?", (uid,))

                delete_where(con, "posts", "user_id=?", (uid,))
                delete_where(con, "reels", "user_id=?", (uid,))

                # Finally delete the account row.
                delete_where(con, "users", "id=? AND id!=1", (uid,))
                result["users_removed"] += 1

        if not dry_run and result["expired_accounts_processed"]:
            save_json_atomic(story_json_path, stories_to_keep)
            save_json_atomic(replies_json_path, replies_to_keep)

        if not dry_run:
            con.commit()
        else:
            con.rollback()

    except Exception:
        try:
            con.rollback()
        except Exception:
            pass

        # Restore original JSON data if cleanup fails.
        if not dry_run:
            try:
                if "all_stories" in locals():
                    save_json_atomic(story_json_path, all_stories)
                if "all_replies" in locals():
                    save_json_atomic(replies_json_path, all_replies)
            except Exception as restore_error:
                print("WARNING: JSON restore failed:", restore_error)

        raise
    finally:
        con.close()

    # Remove files only after the database transaction succeeds.
    if not dry_run and result["expired_accounts_processed"]:
        for path in files_to_remove:
            if os.path.isfile(path):
                try:
                    os.remove(path)
                    result["files_removed"] += 1
                except OSError:
                    pass

    return result
