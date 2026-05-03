import os
import sqlite3
from flask import Blueprint, render_template, request, redirect, url_for, session, flash
from werkzeug.utils import secure_filename
from datetime import datetime

posts_bp = Blueprint("posts", __name__, url_prefix="/posts")

UPLOAD_FOLDER = "static/uploads"
ALLOWED_EXTENSIONS = {"png", "jpg", "jpeg", "gif"}

# STORY IMPORTS
from routes.stories import (
    load_stories_for_feed,
    get_storybar_for_user,
    cleanup_expired
)

# -------------------------
def allowed_file(filename):
    return "." in filename and filename.rsplit(".", 1)[1].lower() in ALLOWED_EXTENSIONS


# ===============================
# 📌 FEED PAGE (UPDATED)
# ===============================
@posts_bp.route("/feed")
def feed():

    if "user_id" not in session:
        return redirect(url_for("auth.login"))

    current_user = session.get("user_id")

    # ✅ USER DP LOAD (NEW FIX)
    photo = "/static/default_dp.png"

    conn2 = sqlite3.connect("database.db")
    conn2.row_factory = sqlite3.Row
    c2 = conn2.cursor()

    c2.execute("SELECT photo FROM users WHERE id=?", (current_user,))
    row = c2.fetchone()

    if row and row["photo"]:
        photo = row["photo"]

    conn2.close()

    # ---- STORY SYSTEM ----
    cleanup_expired()

    stories_bar = get_storybar_for_user(current_user)
    _stories = load_stories_for_feed()

    # -------- POSTS LOAD ----------
    conn = sqlite3.connect("database.db")
    c = conn.cursor()

    # ✅ FIXED QUERY (NOW FETCHES OWNER ID ALSO)
    c.execute("""
        SELECT posts.id, posts.user_id, users.username, users.photo, posts.caption
        FROM posts
        JOIN users ON posts.user_id = users.id
        ORDER BY posts.id DESC
    """)
    rows = c.fetchall()

    posts = []
    for row in rows:
        post_id, owner_id, username, user_photo, caption = row

        c.execute("SELECT image_path FROM post_images WHERE post_id=?", (post_id,))
        images = [r[0] for r in c.fetchall()]

        c.execute("SELECT COUNT(*) FROM likes WHERE post_id=?", (post_id,))
        likes = c.fetchone()[0]

        c.execute("""
            SELECT users.username, comments.comment
            FROM comments
            JOIN users ON comments.user_id = users.id
            WHERE comments.post_id=?
            ORDER BY comments.id ASC
        """, (post_id,))
        comments = [{"username": r[0], "comment": r[1]} for r in c.fetchall()]

        posts.append({
            "id": post_id,
            "owner_id": owner_id,
            "username": username,
            "photo": user_photo if user_photo else "/static/default_dp.png",
            "caption": caption,
            "images": images,
            "likes": likes,
            "comments": comments
        })

    conn.close()

    return render_template(
        "feed.html",
        posts=posts,
        stories_bar=stories_bar,
        current_user=current_user,
        current_user_photo=photo   # ✅ FIXED
    )

# ===============================
# 📌 UPLOAD POST
# ===============================
@posts_bp.route("/upload", methods=["GET", "POST"])
def upload():
    if "user_id" not in session:
        return redirect(url_for("auth.login"))

    if request.method == "POST":
        caption = request.form.get("caption", "")

        conn = sqlite3.connect("database.db")
        c = conn.cursor()

        c.execute("INSERT INTO posts (user_id, caption) VALUES (?, ?)",
                  (session["user_id"], caption))
        post_id = c.lastrowid

        if "images" in request.files:
            for img in request.files.getlist("images"):
                if img.filename and allowed_file(img.filename):
                    filename = secure_filename(img.filename)

                    path = os.path.join(UPLOAD_FOLDER, filename)
                    img.save(path)

                    db_path = "/static/uploads/" + filename

                    c.execute("INSERT INTO post_images (post_id, image_path) VALUES (?, ?)",
                              (post_id, db_path))

        conn.commit()
        conn.close()

        flash("Post uploaded!", "success")
        return redirect(url_for("posts.feed"))

    return render_template("upload.html")


# ===============================
# 🗑 DELETE POST (FIXED)
# ===============================
@posts_bp.route("/delete/<int:post_id>", methods=["POST"])
def delete(post_id):

    if "user_id" not in session:
        return redirect(url_for("auth.login"))

    uid = session["user_id"]

    conn = sqlite3.connect("database.db")
    c = conn.cursor()

    # ✅ FIXED: OWNER CHECK BY user_id NOT username
    c.execute("SELECT user_id FROM posts WHERE id=?", (post_id,))
    row = c.fetchone()

    if not row or row[0] != uid:
        conn.close()
        flash("You cannot delete others' posts!", "error")
        return redirect(url_for("posts.feed"))

    # delete images from disk
    c.execute("SELECT image_path FROM post_images WHERE post_id=?", (post_id,))
    for img in c.fetchall():
        try:
            # db stores /static/uploads/file.jpg
            # convert to real file path static/uploads/file.jpg
            file_path = img[0].replace("/static/", "static/")
            if os.path.exists(file_path):
                os.remove(file_path)
        except:
            pass

    c.execute("DELETE FROM post_images WHERE post_id=?", (post_id,))
    c.execute("DELETE FROM likes WHERE post_id=?", (post_id,))
    c.execute("DELETE FROM comments WHERE post_id=?", (post_id,))
    c.execute("DELETE FROM posts WHERE id=?", (post_id,))

    conn.commit()
    conn.close()

    flash("Post deleted!", "success")
    return redirect(url_for("posts.feed"))


# ===============================
# 💬 COMMENT SYSTEM (FEED)
# ===============================
@posts_bp.route("/comment/<int:post_id>", methods=["POST"])
def comment(post_id):
    if "user_id" not in session:
        return redirect(url_for("auth.login"))

    comment_text = request.form.get("comment", "").strip()
    if not comment_text:
        return redirect(url_for("posts.feed"))

    conn = sqlite3.connect("database.db")
    c = conn.cursor()

    c.execute("INSERT INTO comments (post_id, user_id, comment) VALUES (?, ?, ?)",
              (post_id, session["user_id"], comment_text))

    conn.commit()
    conn.close()
    return redirect(url_for("posts.feed"))


# ===============================
# ❤️ LIKE / UNLIKE (FEED)
# ===============================
@posts_bp.route("/like/<int:post_id>", methods=["POST"])
def like(post_id):
    if "user_id" not in session:
        return redirect(url_for("auth.login"))

    conn = sqlite3.connect("database.db")
    c = conn.cursor()

    c.execute("SELECT id FROM likes WHERE post_id=? AND username=?",
              (post_id, session["user_id"]))
    liked = c.fetchone()

    if liked:
        c.execute("DELETE FROM likes WHERE id=?", (liked[0],))
    else:
        c.execute("INSERT INTO likes (post_id, username) VALUES (?, ?)",
                  (post_id, session["user_id"]))

    conn.commit()
    conn.close()
    return redirect(url_for("posts.feed"))


# ===============================
# 👁 VIEW SINGLE POST
# ===============================
@posts_bp.route("/<int:post_id>")
def view_post(post_id):

    conn = sqlite3.connect("database.db")
    conn.row_factory = sqlite3.Row
    c = conn.cursor()

    # POST DATA
    c.execute("""
        SELECT posts.id, posts.caption, posts.user_id, users.username
        FROM posts
        JOIN users ON posts.user_id = users.id
        WHERE posts.id=?
    """, (post_id,))
    post = c.fetchone()

    if not post:
        conn.close()
        return "Post not found", 404

    # IMAGES
    c.execute("SELECT image_path FROM post_images WHERE post_id=?", (post_id,))
    images = [r["image_path"] for r in c.fetchall()]

    # LIKES COUNT
    c.execute("SELECT COUNT(*) as total FROM likes WHERE post_id=?", (post_id,))
    likes = c.fetchone()["total"]

    # CHECK CURRENT USER LIKED OR NOT
    liked_by_me = False
    if "user_id" in session:
        c.execute("SELECT 1 FROM likes WHERE post_id=? AND username=?",
                  (post_id, session["user_id"]))
        liked_by_me = c.fetchone() is not None

    # CHECK SAVED OR NOT
    saved_by_me = False
    if "user_id" in session:
        c.execute("SELECT 1 FROM post_saves WHERE post_id=? AND user_id=?",
                  (post_id, session["user_id"]))
        saved_by_me = c.fetchone() is not None

    # COMMENTS (FIXED WITH COMMENT ID + USER ID)
    c.execute("""
        SELECT comments.id, comments.user_id, users.username, comments.comment
        FROM comments
        JOIN users ON comments.user_id = users.id
        WHERE comments.post_id=?
        ORDER BY comments.id DESC
    """, (post_id,))
    comments = [{
        "id": r["id"],
        "user_id": r["user_id"],
        "username": r["username"],
        "comment": r["comment"]
    } for r in c.fetchall()]

    conn.close()

    return render_template(
        "post_view.html",
        post=post,
        images=images,
        likes=likes,
        comments=comments,
        liked_by_me=liked_by_me,
        saved_by_me=saved_by_me,
        current_user=session.get("user_id")
    )


# ===============================
# ❤️ LIKE / UNLIKE FROM POST VIEW
# ===============================
@posts_bp.route("/like_toggle/<int:post_id>", methods=["POST"])
def like_toggle(post_id):

    if "user_id" not in session:
        return redirect(url_for("auth.login"))

    conn = sqlite3.connect("database.db")
    c = conn.cursor()

    # Check if already liked
    c.execute("SELECT id FROM likes WHERE post_id=? AND username=?",
              (post_id, session["user_id"]))
    liked = c.fetchone()

    if liked:
        c.execute("DELETE FROM likes WHERE id=?", (liked[0],))
    else:
        c.execute("INSERT INTO likes (post_id, username) VALUES (?, ?)",
                  (post_id, session["user_id"]))

    conn.commit()
    conn.close()

    return redirect(f"/posts/{post_id}")


# ===============================
# 💬 COMMENT FROM POST VIEW
# ===============================
@posts_bp.route("/comment_view/<int:post_id>", methods=["POST"])
def comment_view(post_id):

    if "user_id" not in session:
        return redirect(url_for("auth.login"))

    comment_text = request.form.get("comment", "").strip()
    if not comment_text:
        return redirect(f"/posts/{post_id}")

    conn = sqlite3.connect("database.db")
    c = conn.cursor()

    c.execute("INSERT INTO comments (post_id, user_id, comment) VALUES (?, ?, ?)",
              (post_id, session["user_id"], comment_text))

    conn.commit()
    conn.close()

    return redirect(f"/posts/{post_id}")


# ===============================
# 🗑 DELETE COMMENT (NEW)
# ===============================
@posts_bp.route("/comment_delete/<int:comment_id>/<int:post_id>", methods=["POST"])
def comment_delete(comment_id, post_id):

    if "user_id" not in session:
        return redirect(url_for("auth.login"))

    uid = session["user_id"]

    conn = sqlite3.connect("database.db")
    c = conn.cursor()

    c.execute("SELECT user_id FROM comments WHERE id=?", (comment_id,))
    row = c.fetchone()

    if not row or row[0] != uid:
        conn.close()
        flash("You cannot delete others comment!", "error")
        return redirect(f"/posts/{post_id}")

    c.execute("DELETE FROM comments WHERE id=?", (comment_id,))
    conn.commit()
    conn.close()

    flash("Comment deleted!", "success")
    return redirect(f"/posts/{post_id}")


# ===============================
# 👥 GET FOLLOWERS LIST (FOR SHARE POPUP)
# ===============================
@posts_bp.route("/get_followers")
def get_followers():

    if "user_id" not in session:
        return {"ok": False, "error": "login required"}

    uid = session["user_id"]

    conn = sqlite3.connect("database.db")
    conn.row_factory = sqlite3.Row
    c = conn.cursor()

    # users who follow me
    c.execute("""
        SELECT users.id, users.username
        FROM follows
        JOIN users ON follows.follower_id = users.id
        WHERE follows.following_id=?
        ORDER BY users.username ASC
    """, (uid,))

    followers = [{"id": r["id"], "username": r["username"]} for r in c.fetchall()]
    conn.close()

    return {"ok": True, "followers": followers}


# ===============================
# 📤 SHARE POST TO USER (SEND IN DM)
# ===============================
@posts_bp.route("/share_to_user", methods=["POST"])
def share_to_user():

    if "user_id" not in session:
        return {"ok": False, "error": "login required"}

    from_user = session["user_id"]
    data = request.get_json()

    to_user_id = data.get("to_user_id")
    post_id = data.get("post_id")

    if not to_user_id or not post_id:
        return {"ok": False, "error": "missing data"}

    # message text (post link)
    msg = f"📌 Shared a post: /posts/{post_id}"

    conn = sqlite3.connect("database.db")
    c = conn.cursor()

    # INSERT into messages table
    c.execute("""
        INSERT INTO messages (sender_id, receiver_id, message, timestamp, seen)
        VALUES (?, ?, ?, datetime('now'), 0)
    """, (from_user, to_user_id, msg))

    conn.commit()
    conn.close()

    return {"ok": True}


# ===============================
# 🔖 SAVE / UNSAVE POST
# ===============================
@posts_bp.route("/save_toggle/<int:post_id>", methods=["POST"])
def save_toggle(post_id):

    if "user_id" not in session:
        return {"ok": False, "error": "login required"}

    uid = session["user_id"]

    conn = sqlite3.connect("database.db")
    c = conn.cursor()

    c.execute("SELECT id FROM post_saves WHERE post_id=? AND user_id=?", (post_id, uid))
    row = c.fetchone()

    if row:
        c.execute("DELETE FROM post_saves WHERE id=?", (row[0],))
        action = "unsaved"
    else:
        c.execute("INSERT INTO post_saves (post_id, user_id) VALUES (?, ?)", (post_id, uid))
        action = "saved"

    conn.commit()
    conn.close()

    return {"ok": True, "action": action}
