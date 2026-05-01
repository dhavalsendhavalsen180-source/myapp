# routes/profile.py
from flask import Blueprint, render_template, request, redirect, session
import sqlite3, os
from werkzeug.utils import secure_filename

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

    # USER DATA
    c.execute("SELECT id, username, bio, photo FROM users WHERE id=?", (user_id,))
    u = c.fetchone()

    if not u:
        conn.close()
        return "User not found", 404

    profile_data = {
        "id": u["id"],
        "username": u["username"],
        "bio": u["bio"] or "",
        "photo": u["photo"] if u["photo"] else "/static/default_dp.jpg"
    }

    # POSTS
    c.execute("SELECT id FROM posts WHERE user_id=? ORDER BY id DESC", (user_id,))
    post_ids = c.fetchall()

    posts = []
    for p in post_ids:
        c.execute("SELECT image_path FROM post_images WHERE post_id=? LIMIT 1", (p["id"],))
        img = c.fetchone()
        posts.append({
            "id": p["id"],
            "image": img["image_path"] if img else None
        })

    # REELS
    c.execute("""
        SELECT id, video_path, caption
        FROM reels
        WHERE user_id=?
        ORDER BY id DESC
    """, (user_id,))

    reels_rows = c.fetchall()

    reels = []
    for r in reels_rows:
        reels.append({
            "id": r["id"],
            "video": r["video_path"],
            "caption": r["caption"] or ""
        })

    # FOLLOWERS / FOLLOWING
    c.execute("SELECT COUNT(*) as total FROM follows WHERE following_id=?", (user_id,))
    followers = c.fetchone()["total"]

    c.execute("SELECT COUNT(*) as total FROM follows WHERE follower_id=?", (user_id,))
    following = c.fetchone()["total"]

    # CHECK IF CURRENT USER FOLLOWS
    current = session.get("user_id")
    is_following = False

    if current and current != user_id:
        c.execute("SELECT 1 FROM follows WHERE follower_id=? AND following_id=?", (current, user_id))
        is_following = c.fetchone() is not None

    conn.close()

    return render_template(
        "profile.html",
        profile=profile_data,
        posts=posts,
        reels=reels,
        followers=followers,
        following=following,
        is_following=is_following,
        current_user=current
    )


# ------------------ EDIT PROFILE ------------------ #
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

    # PHOTO UPDATE
    if photo and photo.filename and allowed_file(photo.filename):
        ext = photo.filename.rsplit(".", 1)[1].lower()
        filename = secure_filename(f"user_{uid}.{ext}")
        save_path = os.path.join(UPLOAD_FOLDER, filename)

        photo.save(save_path)

        photo_url = "/" + save_path.replace("\\", "/")
        c.execute("UPDATE users SET photo=? WHERE id=?", (photo_url, uid))

    # USERNAME + BIO UPDATE
    if username:
        c.execute("UPDATE users SET username=?, bio=? WHERE id=?", (username, bio, uid))
    else:
        c.execute("UPDATE users SET bio=? WHERE id=?", (bio, uid))

    conn.commit()
    conn.close()

    return redirect(f"/profile/{uid}")

# ------------------ FOLLOWERS LIST ------------------ #
@profile_bp.route("/<int:user_id>/followers")
def followers_list(user_id):

    conn = sqlite3.connect("database.db")
    conn.row_factory = sqlite3.Row
    c = conn.cursor()

    c.execute("SELECT id, username, photo FROM users WHERE id=?", (user_id,))
    user = c.fetchone()
    if not user:
        conn.close()
        return "User not found", 404

    c.execute("""
        SELECT u.id, u.username, u.photo
        FROM follows f
        JOIN users u ON f.follower_id = u.id
        WHERE f.following_id=?
        ORDER BY f.id DESC
    """, (user_id,))
    followers = c.fetchall()

    conn.close()

    return render_template(
        "profile.html",
        profile=profile_data,
        posts=posts,
        reels=reels,
        followers=followers,
        following=following,
        is_following=is_following,
        current_user=current
    )
def following_list(user_id):

    conn = sqlite3.connect("database.db")
    conn.row_factory = sqlite3.Row
    c = conn.cursor()

    c.execute("SELECT id, username, photo FROM users WHERE id=?", (user_id,))
    user = c.fetchone()
    if not user:
        conn.close()
        return "User not found", 404

    c.execute("""
        SELECT u.id, u.username, u.photo
        FROM follows f
        JOIN users u ON f.following_id = u.id
        WHERE f.follower_id=?
        ORDER BY f.id DESC
    """, (user_id,))
    following = c.fetchall()

    conn.close()

    return render_template(
        "profile.html",
        profile=profile_data,
        posts=posts,
        reels=reels,
        followers=followers,
        following=following,
        is_following=is_following,
        current_user=current
    )
def settings_page():
    if "user_id" not in session:
        return redirect("/auth/login")

    return render_template(
        "profile.html",
        profile=profile_data,
        posts=posts,
        reels=reels,
        followers=followers,
        following=following,
        is_following=is_following,
        current_user=current
    )
def saved_page():
    if "user_id" not in session:
        return redirect("/auth/login")

    uid = session["user_id"]

    conn = sqlite3.connect(DB_NAME)
    conn.row_factory = sqlite3.Row
    c = conn.cursor()

    # Get saved post ids
    c.execute("""
        SELECT posts.id, posts.caption
        FROM post_saves
        JOIN posts ON post_saves.post_id = posts.id
        WHERE post_saves.user_id=?
        ORDER BY post_saves.id DESC
    """, (uid,))

    rows = c.fetchall()

    saved_posts = []
    for r in rows:
        post_id = r["id"]

        # Get first image
        c.execute("SELECT image_path FROM post_images WHERE post_id=? LIMIT 1", (post_id,))
        img = c.fetchone()

        saved_posts.append({
            "id": post_id,
            "caption": r["caption"],
            "image": img["image_path"] if img else None
        })

    conn.close()
################₹############

@profile_bp.route("/saved/reels")
def saved_reels():
    uid = session["user_id"]

    conn = sqlite3.connect(DB_NAME)
    conn.row_factory = sqlite3.Row
    c = conn.cursor()

    c.execute("""
        SELECT r.*
        FROM reel_saves s
        JOIN reels r ON r.id = s.reel_id
        WHERE s.user_id=?
    """, (uid,))

    reels = c.fetchall()
    conn.close()

    return render_template("saved_reels.html", reels=reels)
