import os
import sqlite3
from flask import Blueprint, render_template, request, redirect, url_for, session, flash
from werkzeug.utils import secure_filename

posts_bp = Blueprint("posts", __name__, url_prefix="/posts")

UPLOAD_FOLDER = "static/uploads"
ALLOWED_EXTENSIONS = {"png", "jpg", "jpeg", "gif"}

# ✅ Helper: allowed file check
def allowed_file(filename):
    return "." in filename and filename.rsplit(".", 1)[1].lower() in ALLOWED_EXTENSIONS

# ✅ Feed route

@posts_bp.route("/feed")
def feed():
    if "user_id" not in session:   # ✅ ab user_id check kar
        return redirect(url_for("auth.login"))

    conn = sqlite3.connect("database.db")
    c = conn.cursor()

    # Get posts with username
    c.execute("""
        SELECT posts.id, users.username, posts.caption
        FROM posts
        JOIN users ON posts.user_id = users.id
        ORDER BY posts.id DESC
    """)
    rows = c.fetchall()

    posts = []
    for row in rows:
        post_id, username, caption = row

        # Get images
        c.execute("SELECT image_path FROM post_images WHERE post_id=?", (post_id,))
        images = [r[0] for r in c.fetchall()]

        # Get likes
        c.execute("SELECT COUNT(*) FROM likes WHERE post_id=?", (post_id,))
        likes = c.fetchone()[0]

        # Get comments
        c.execute("SELECT username, comment FROM comments WHERE post_id=?", (post_id,))
        comments = [{"username": r[0], "comment": r[1]} for r in c.fetchall()]

        # ✅ Consistent dict keys
        posts.append({
            "id": post_id,
            "user": username,      # ⚡ feed.html me post.user use hoga
            "caption": caption,
            "images": images,
            "likes": likes,
            "comments": comments
        })

    conn.close()

    return render_template(
        "feed.html",
        posts=posts,
        current_user=session["user"]   # ✅ username session me
    )



# ✅ Upload post (multi-image)

@posts_bp.route("/upload", methods=["GET", "POST"])
def upload():
    if "user_id" not in session:
        return redirect(url_for("auth.login"))

    if request.method == "POST":
        caption = request.form["caption"]

        conn = sqlite3.connect("database.db")
        c = conn.cursor()
        c.execute("INSERT INTO posts (user_id, caption) VALUES (?, ?)",
                  (session["user_id"], caption))
        post_id = c.lastrowid

        # Save images if uploaded
        if "images" in request.files:
            for img in request.files.getlist("images"):
                filename = secure_filename(img.filename)
                path = os.path.join("static/uploads", filename)
                img.save(path)

                c.execute(
                    "INSERT INTO post_images (post_id, image_path) VALUES (?, ?)",
                    (post_id, path)
                )

        conn.commit()
        conn.close()

        flash("Post uploaded!", "success")
        return redirect(url_for("posts.feed"))

    # GET → show upload form
    return render_template("upload.html")

# ✅ Delete post
@posts_bp.route("/delete/<int:post_id>", methods=["POST"])
def delete(post_id):
    if "user" not in session:
        return redirect(url_for("auth.login"))

    conn = sqlite3.connect("database.db")
    c = conn.cursor()

    # Check owner
    c.execute("SELECT username FROM posts WHERE id=?", (post_id,))
    row = c.fetchone()
    if not row:
        conn.close()
        flash("Post not found!", "error")
        return redirect(url_for("posts.feed"))

    if row[0] != session["user"]:
        conn.close()
        flash("You cannot delete others' posts!", "error")
        return redirect(url_for("posts.feed"))

    # Delete images from disk + db
    c.execute("SELECT image_path FROM post_images WHERE post_id=?", (post_id,))
    for img_row in c.fetchall():
        try:
            os.remove(img_row[0])
        except:
            pass
    c.execute("DELETE FROM post_images WHERE post_id=?", (post_id,))

    # Delete likes + comments
    c.execute("DELETE FROM likes WHERE post_id=?", (post_id,))
    c.execute("DELETE FROM comments WHERE post_id=?", (post_id,))

    # Delete post
    c.execute("DELETE FROM posts WHERE id=?", (post_id,))
    conn.commit()
    conn.close()

    flash("Post deleted!", "success")
    return redirect(url_for("posts.feed"))
