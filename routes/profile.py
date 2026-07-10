from flask import Blueprint, render_template, request, redirect, session
import sqlite3, os
from werkzeug.utils import secure_filename
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
        SELECT id, username, bio, photo, is_private
        FROM users
        WHERE id=?
    """, (user_id,))

    u = c.fetchone()

    if not u:
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

    # PRIVATE ACCOUNT CHECK
    can_view = True

    if profile_data["is_private"] == 1:
        if current != user_id and not is_following:
            can_view = False

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
        current_user=current,
        can_view=can_view,
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

    c.execute("SELECT id, username, photo FROM users WHERE id=?", (user_id,))
    u = c.fetchone()

    if not u:
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

    c.execute("SELECT id, username, photo FROM users WHERE id=?", (user_id,))
    u = c.fetchone()

    if not u:
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
        JOIN posts ON post_saves.post_id = posts.id
        WHERE post_saves.user_id=?
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

    # SAVED REELS
    c.execute("""
        SELECT r.*
        FROM reel_saves rs
        JOIN reels r ON r.id = rs.reel_id
        WHERE rs.user_id=?
        ORDER BY rs.id DESC
    """, (uid,))

    saved_reels = c.fetchall()

    conn.close()

    return render_template(
        "saved.html",
        saved_posts=saved_posts,
        saved_reels=saved_reels
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
