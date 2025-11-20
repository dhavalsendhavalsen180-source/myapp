import os
import json
import sqlite3
from flask import Blueprint, request, session, redirect, url_for, jsonify, render_template, flash
from werkzeug.utils import secure_filename

social_bp = Blueprint("social", __name__, url_prefix="/social")

UPLOAD_FOLDER = "static/uploads"
ALLOWED_EXT = {"png", "jpg", "jpeg", "gif", "mp4"}

# -------------------- DB Helper --------------------
def get_conn():
    return sqlite3.connect("database.db")

def allowed_file(fname):
    return "." in fname and fname.rsplit(".", 1)[1].lower() in ALLOWED_EXT


# ==============================================================
# 🔥 LIKE / UNLIKE (AJAX)
# ==============================================================

@social_bp.route("/posts/like/<int:post_id>", methods=["POST"])
def like_post(post_id):
    if "user_id" not in session:
        return jsonify({"ok": False, "error": "login_required"}), 401

    user_id = session["user_id"]
    conn = get_conn()
    c = conn.cursor()

    c.execute("SELECT id FROM likes WHERE post_id=? AND user_id=?", (post_id, user_id))
    row = c.fetchone()

    if row:
        c.execute("DELETE FROM likes WHERE id=?", (row[0],))

        # new updated count
        c.execute("SELECT COUNT(*) FROM likes WHERE post_id=?", (post_id,))
        like_count = c.fetchone()[0]

        conn.commit()
        conn.close()
        return jsonify({"ok": True, "action": "unliked", "count": like_count})

    else:
        c.execute("INSERT INTO likes (post_id, user_id, username) VALUES (?, ?, ?)",
                  (post_id, user_id, session.get("user")))

        # owner notification
        c.execute("SELECT user_id FROM posts WHERE id=?", (post_id,))
        owner = c.fetchone()
        if owner and owner[0] != user_id:
            meta = json.dumps({"post_id": post_id})
            c.execute(
                "INSERT INTO notifications (user_id, actor_id, type, meta) VALUES (?, ?, ?, ?)",
                (owner[0], user_id, "like", meta)
            )

        # updated count
        c.execute("SELECT COUNT(*) FROM likes WHERE post_id=?", (post_id,))
        like_count = c.fetchone()[0]

        conn.commit()
        conn.close()
        return jsonify({"ok": True, "action": "liked", "count": like_count})

# ==============================================================
# 💬 COMMENT
# ==============================================================

@social_bp.route("/posts/comment/<int:post_id>", methods=["POST"])
def comment_post(post_id):
    if "user_id" not in session:
        return redirect(url_for("auth.login"))

    text = request.form.get("comment", "").strip()
    if not text:
        return redirect(url_for("posts.feed"))

    conn = get_conn()
    c = conn.cursor()

    c.execute(
        "INSERT INTO comments (post_id, user_id, username, comment) VALUES (?, ?, ?, ?)",
        (post_id, session["user_id"], session["user"], text)
    )
    comment_id = c.lastrowid

    # Notify post owner
    c.execute("SELECT user_id FROM posts WHERE id=?", (post_id,))
    owner = c.fetchone()
    if owner and owner[0] != session["user_id"]:
        meta = json.dumps({"post_id": post_id, "comment_id": comment_id})
        c.execute(
            "INSERT INTO notifications (user_id, actor_id, type, meta) VALUES (?, ?, ?, ?)",
            (owner[0], session["user_id"], "comment", meta)
        )

    conn.commit()
    conn.close()
    return redirect(url_for("posts.feed"))


# ==============================================================
# 👤 FOLLOW / UNFOLLOW
# ==============================================================

@social_bp.route("/follow/<int:target_id>", methods=["POST"])
def follow_toggle(target_id):
    if "user_id" not in session:
        return redirect(url_for("auth.login"))

    me = session["user_id"]

    if me == target_id:
        return jsonify({"ok": False, "error": "self"}), 400

    conn = get_conn()
    c = conn.cursor()

    c.execute("SELECT id FROM follows WHERE follower_id=? AND following_id=?", (me, target_id))
    row = c.fetchone()

    if row:
        # Unfollow
        c.execute("DELETE FROM follows WHERE id=?", (row[0],))
        conn.commit()
        conn.close()
        return jsonify({"ok": True, "action": "unfollowed"})

    else:
        # Follow
        c.execute(
            "INSERT INTO follows (follower_id, following_id) VALUES (?, ?)",
            (me, target_id)
        )

        # Notify follow target
        c.execute(
            "INSERT INTO notifications (user_id, actor_id, type, meta) VALUES (?, ?, ?, ?)",
            (target_id, me, "follow", json.dumps({}))
        )

        conn.commit()
        conn.close()
        return jsonify({"ok": True, "action": "followed"})


# ==============================================================
# 📸 PROFILE PAGE (username)
# ==============================================================

@social_bp.route("/u/<username>")
def profile(username):
    conn = get_conn()
    c = conn.cursor()

    c.execute("SELECT id, username FROM users WHERE username=?", (username,))
    u = c.fetchone()
    if not u:
        conn.close()
        return "User not found", 404

    user_id = u[0]

    # Posts
    c.execute("SELECT id, caption FROM posts WHERE user_id=? ORDER BY id DESC", (user_id,))
    rows = c.fetchall()

    posts = []
    for pid, caption in rows:
        c.execute("SELECT image_path FROM post_images WHERE post_id=?", (pid,))
        images = [x[0] for x in c.fetchall()]

        c.execute("SELECT COUNT(*) FROM likes WHERE post_id=?", (pid,))
        likes = c.fetchone()[0]

        posts.append({"id": pid, "caption": caption, "images": images, "likes": likes})

    # Check if requester follows this profile
    c.execute("SELECT id FROM follows WHERE follower_id=? AND following_id=?", (session.get("user_id", 0), user_id))
    is_following = bool(c.fetchone())

    conn.close()
    return render_template(
        "profile.html",
        profile={"id": user_id, "username": username},
        posts=posts,
        is_following=is_following
    )


# ==============================================================
# 🟧 STORIES (UPLOAD + FEED)
# ==============================================================

@social_bp.route("/stories/upload", methods=["GET", "POST"])
def upload_story():
    if "user_id" not in session:
        return redirect(url_for("auth.login"))

    if request.method == "POST":
        if "story" not in request.files:
            flash("No file selected", "error")
            return redirect(url_for("social.upload_story"))

        f = request.files["story"]

        if allowed_file(f.filename):
            filename = secure_filename(f.filename)
            save_path = os.path.join(UPLOAD_FOLDER, filename)
            f.save(save_path)

            conn = get_conn()
            c = conn.cursor()

            c.execute("""
              INSERT INTO stories (user_id, media_path, expires_at)
              VALUES (?, ?, datetime('now','+1 day'))
            """, (session["user_id"], save_path))

            conn.commit()
            conn.close()

            flash("Story uploaded!", "success")
            return redirect(url_for("social.upload_story"))

    return render_template("upload_story.html")


@social_bp.route("/stories")
def stories_feed():
    conn = get_conn()
    c = conn.cursor()

    c.execute("""
        SELECT stories.id, users.username, stories.media_path, stories.created_at
        FROM stories
        JOIN users ON stories.user_id = users.id
        WHERE datetime('now') < stories.expires_at
        ORDER BY stories.created_at DESC
    """)

    rows = c.fetchall()
    conn.close()

    stories = [{
        "id": r[0],
        "user": r[1],
        "media": r[2],
        "created_at": r[3]
    } for r in rows]

    return jsonify({"ok": True, "stories": stories})


# ==============================================================
# 🔔 NOTIFICATIONS
# ==============================================================

@social_bp.route("/notifications")
def notifications():
    if "user_id" not in session:
        return redirect(url_for("auth.login"))

    conn = get_conn()
    c = conn.cursor()

    c.execute("""
        SELECT id, actor_id, type, meta, is_read, created_at
        FROM notifications
        WHERE user_id=?
        ORDER BY created_at DESC
    """, (session["user_id"],))

    nots = [{
        "id": r[0],
        "actor_id": r[1],
        "type": r[2],
        "meta": r[3],
        "is_read": r[4],
        "created_at": r[5]
    } for r in c.fetchall()]

    conn.close()

    return render_template("notifications.html", notifications=nots)


@social_bp.route("/notifications/mark_read/<int:not_id>", methods=["POST"])
def mark_read(not_id):
    if "user_id" not in session:
        return jsonify({"ok": False}), 401

    conn = get_conn()
    c = conn.cursor()
    c.execute("UPDATE notifications SET is_read=1 WHERE id=? AND user_id=?", (not_id, session["user_id"]))
    conn.commit()
    conn.close()
    return jsonify({"ok": True})


# ==============================================================
# 🔍 EXPLORE PAGE
# ==============================================================

@social_bp.route("/explore")
def explore():
    conn = get_conn()
    c = conn.cursor()

    c.execute("""
       SELECT posts.id, users.username, posts.caption, COUNT(likes.id) as likecount
       FROM posts
       LEFT JOIN likes ON posts.id = likes.post_id
       JOIN users ON posts.user_id = users.id
       GROUP BY posts.id
       ORDER BY likecount DESC, posts.id DESC
       LIMIT 50
    """)

    rows = c.fetchall()
    conn.close()

    posts = [{
        "id": r[0],
        "user": r[1],
        "caption": r[2],
        "likes": r[3]
    } for r in rows]

    return render_template("explore.html", posts=posts)
