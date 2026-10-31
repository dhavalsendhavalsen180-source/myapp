import os
import sqlite3
import json
from flask import Blueprint, render_template, request, redirect, url_for, session, flash
from werkzeug.utils import secure_filename
from datetime import datetime
from flask import jsonify

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

    current_user = session["user_id"]

    conn = sqlite3.connect("database.db")
    c = conn.cursor()

    c.execute(
        "SELECT id FROM users WHERE id=?",
        (current_user,)
    )

    user = c.fetchone()

    if not user:
        session.clear()
        flash("Your session has expired. Please log in again.", "error")
        return redirect(url_for("auth.login"))

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

    stories = load_stories_for_feed()

    my_story_seen = False

    my_stories = [
        s for s in stories
        if str(s.get("user_id")) == str(current_user)
    ]

    if my_stories:

        my_story_seen = True

        for s in my_stories:

            viewers = [str(v) for v in s.get("viewers", [])]

            if str(current_user) not in viewers:
                my_story_seen = False
                break

    has_my_story = len(my_stories) > 0

    stories_bar = get_storybar_for_user(current_user)

    # -------- POSTS LOAD ----------
    conn = sqlite3.connect("database.db")
    c = conn.cursor()

    # ✅ FIXED QUERY (NOW FETCHES OWNER ID ALSO)
    c.execute("""
        SELECT
            posts.id,
            posts.user_id,
            users.username,
            users.photo,
            posts.caption,
            users.is_private
        FROM posts
        JOIN users
            ON posts.user_id = users.id

        WHERE
            COALESCE(users.suspended, 0) = 0
            AND COALESCE(users.banned, 0) = 0
            AND users.deletion_requested_at IS NULL
            AND (
                posts.user_id = ?
                OR users.is_private = 0
                OR (
                    users.is_private = 1
                    AND EXISTS (
                        SELECT 1
                        FROM follows
                        WHERE follows.follower_id = ?
                          AND follows.following_id = posts.user_id
                    )
                )
            )

        ORDER BY posts.id DESC
    """, (
        current_user,
        current_user
    ))
    rows = c.fetchall()

    posts = []

    for row in rows:
        post_id, owner_id, username, user_photo, caption, is_private = row

        c.execute(
            "SELECT image_path FROM post_images WHERE post_id=?",
            (post_id,)
        )
        images = [r[0] for r in c.fetchall()]

        c.execute(
            "SELECT COUNT(*) FROM likes WHERE post_id=?",
            (post_id,)
        )
        likes = c.fetchone()[0]

        # feed post like
        c.execute("""
            SELECT 1
            FROM likes
            WHERE post_id=? AND username=?
        """, (post_id, current_user))

        liked_by_me = c.fetchone() is not None

#post save clor change reset nahi hoga #
        c.execute(
            "SELECT 1 FROM post_saves WHERE post_id=? AND user_id=?",
            (post_id, current_user)
        )

        saved_by_me = c.fetchone() is not None

        c.execute("""
            SELECT users.username, comments.comment
            FROM comments
            JOIN users ON comments.user_id = users.id
            WHERE comments.post_id=?
            ORDER BY comments.id ASC
        """, (post_id,))
        comments = [{"username": r[0], "comment": r[1]} for r in c.fetchall()]

        owner_stories = [
            s for s in stories
            if str(s.get("user_id")) == str(owner_id)
        ]

        print(owner_id, current_user, len(owner_stories), [s.get("viewers", []) for s in owner_stories])

        # ===============================
        # 🎵 LOAD ATTACHED AUDIO
        # Normal music + Original extracted audio
        # ===============================
        c.execute("""
            SELECT
                ma.music_id,
                ma.original_audio_id,
                ma.original_volume,
                ma.music_volume,
                ma.start_time,
                ma.end_time,

                m.filename AS music_filename,

                oa.audio_file AS original_audio_file,
                oa.title AS original_audio_title,
                oa.user_id AS original_audio_user_id

            FROM media_audio ma

            LEFT JOIN music m
                ON ma.music_id = m.id

            LEFT JOIN original_audio oa
                ON ma.original_audio_id = oa.id

            WHERE ma.media_type='post'
              AND ma.media_id=?

            LIMIT 1
        """, (post_id,))

        audio = c.fetchone()

        print("========== FEED AUDIO DEBUG ==========")
        print("POST ID:", post_id)
        print("AUDIO ROW:", tuple(audio) if audio else None)
        print("======================================")

        # ===============================
        # 🎵 DETERMINE AUDIO FILE
        # ===============================
        music_file = None
        audio_type = None
        original_audio_id = None
        original_audio_title = None
        original_audio_user_id = None

        if audio:

            # Normal music
            if audio[0] and audio[6]:

                music_file = (
                    "/static/music/uploads/" +
                    audio[6]
                )

                audio_type = "music"

            # Original extracted audio
            elif audio[1] and audio[7]:

                music_file = (
                    "/static/uploads/original_audio/" +
                    audio[7]
                )

                audio_type = "original"

                original_audio_id = audio[1]
                original_audio_title = audio[8]
                original_audio_user_id = audio[9]

        posts.append({
            "id": post_id,
            "owner_id": owner_id,
            "username": username,
            "photo": (
                user_photo
                if user_photo
                else "/static/default_dp.png"
            ),
            "caption": caption,
            "images": images,
            "likes": likes,
            "liked_by_me": liked_by_me,
            "saved_by_me": saved_by_me,
            "comments": comments,

            # 🎵 MUSIC INFO
            "music_id": (
                audio[0]
                if audio and audio_type == "music"
                else None
            ),
            "music_title": (
                audio[1]
                if audio and audio_type == "music"
                else None
            ),

            # 🎵 AUDIO FILE
            "music_file": music_file,

            "music_start": (
                audio[4]
                if audio
                else 0
            ),
            "music_end": (
                audio[5]
                if audio
                else 30
            ),
            "original_volume": (
                audio[2]
                if audio
                else 100
            ),
            "music_volume": (
                audio[3]
                if audio
                else 100
            ),

            # AUDIO TYPE
            "audio_type": audio_type,

            # ORIGINAL AUDIO INFO
            "original_audio_id": original_audio_id,
            "original_audio_title": original_audio_title,
            "original_audio_user_id": original_audio_user_id,

            "has_story": (
                len(owner_stories) > 0
            ),

            # True sirf tab hoga
            # jab owner's HAR story dekh li ho
            "story_seen": (
                len(owner_stories) > 0
                and all(
                    str(current_user)
                    in [
                        str(v)
                        for v in s.get(
                            "viewers",
                            []
                        )
                    ]
                    for s in owner_stories
                )
                for s in owner_stories
            )
        })

    conn.close()

    return render_template(
        "feed.html",
        posts=posts,
        stories_bar=stories_bar,
        current_user=current_user,
        current_user_photo=photo,
        my_story_seen=my_story_seen,
        has_my_story=has_my_story
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
# ❤️ LIKE / UNLIKE (FEED)
# ===============================
@posts_bp.route("/like/<int:post_id>", methods=["POST"])
def like(post_id):

    if "user_id" not in session:
        return redirect(url_for("auth.login"))

    uid = session["user_id"]

    conn = sqlite3.connect("database.db")
    c = conn.cursor()

    # Get post owner
    c.execute("""
        SELECT user_id
        FROM posts
        WHERE id=?
    """, (post_id,))

    post_row = c.fetchone()

    if not post_row:
        conn.close()
        return redirect(url_for("posts.feed"))

    post_owner_id = post_row[0]

    # Check existing like
    c.execute("""
        SELECT id
        FROM likes
        WHERE post_id=?
          AND username=?
    """, (post_id, uid))

    liked = c.fetchone()

    if liked:

        # UNLIKE
        c.execute("""
            DELETE FROM likes
            WHERE id=?
        """, (liked[0],))

    else:

        # LIKE
        c.execute("""
            INSERT INTO likes
            (
                post_id,
                username
            )
            VALUES (?, ?)
        """, (
            post_id,
            uid
        ))

        # 🔔 POST LIKE NOTIFICATION
        # Apne hi post ko like karne par notification nahi
        if post_owner_id != uid:

            meta = {
                "post_id": post_id
            }

            c.execute("""
                INSERT INTO notifications
                (
                    user_id,
                    actor_id,
                    type,
                    meta
                )
                VALUES (?, ?, ?, ?)
            """, (
                post_owner_id,
                uid,
                "post_like",
                json.dumps(meta)
            ))

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

    # POSTS DATA (Clicked post first, then all posts)

    # Get clicked post owner
    c.execute(
        "SELECT user_id FROM posts WHERE id=?",
        (post_id,)
    )

    row = c.fetchone()

    if not row:
        conn.close()
        return "Post not found", 404

    owner_id = row["user_id"]

    c.execute(
        """
        SELECT COALESCE(suspended, 0), COALESCE(banned, 0)
        FROM users
        WHERE id = ?
        """,
        (owner_id,)
    )
    status_row = c.fetchone()

    if not status_row or status_row[0] or status_row[1]:
        conn.close()
        return "Post not found", 404

    # Load only this owner's posts
    c.execute("""
        SELECT
            posts.id,
            posts.caption,
            posts.user_id,
            users.username,
            users.photo
        FROM posts
        JOIN users
            ON posts.user_id = users.id
        WHERE posts.user_id=?
        ORDER BY
            CASE WHEN posts.id=? THEN 0 ELSE 1 END,
            posts.id DESC
    """, (owner_id, post_id))

    all_posts = c.fetchall()

    post = all_posts[0]

    # IMAGES + LIKES + SAVE FOR ALL POSTS
    posts = []

    for p in all_posts:

        pid = p["id"]

        # Images
        c.execute(
            "SELECT image_path FROM post_images WHERE post_id=?",
            (pid,)
        )
        images = [x["image_path"] for x in c.fetchall()]

        # Likes
        c.execute(
            "SELECT COUNT(*) AS total FROM likes WHERE post_id=?",
            (pid,)
        )
        likes = c.fetchone()["total"]

        # Liked
        liked = False
        if "user_id" in session:
            c.execute(
                "SELECT 1 FROM likes WHERE post_id=? AND username=?",
                (pid, session["user_id"])
            )
            liked = c.fetchone() is not None

        # Saved
        saved = False
        if "user_id" in session:
            c.execute(
                "SELECT 1 FROM post_saves WHERE post_id=? AND user_id=?",
                (pid, session["user_id"])
            )
            saved = c.fetchone() is not None

        posts.append({
            **dict(p),
            "images": images,
            "likes": likes,
            "liked_by_me": liked,
            "saved_by_me": saved
        })

    post = posts[0]

    # MUSIC / ORIGINAL AUDIO
    c.execute("""
        SELECT
            ma.music_id,
            ma.original_audio_id,
            ma.original_volume,
            ma.music_volume,
            ma.start_time,
            ma.end_time,

            m.filename AS music_filename,
            m.title AS music_title,

            oa.audio_file AS original_audio_file,
            oa.title AS original_audio_title

        FROM media_audio ma

        LEFT JOIN music m
            ON ma.music_id = m.id

        LEFT JOIN original_audio oa
            ON ma.original_audio_id = oa.id

        WHERE ma.media_type='post'
          AND ma.media_id=?

        ORDER BY ma.id DESC
        LIMIT 1
    """, (post["id"],))

    audio = c.fetchone()

    owner_id = post["user_id"]

    # OWNER POSTS
    c.execute("""
        SELECT id, caption
        FROM posts
        WHERE user_id=?
        ORDER BY id DESC
    """, (owner_id,))

    owner_posts = []

    for p in c.fetchall():

        c.execute(
            "SELECT image_path FROM post_images WHERE post_id=?",
            (p["id"],)
        )

        imgs = [x["image_path"] for x in c.fetchall()]

        owner_posts.append({
            "id": p["id"],
            "caption": p["caption"],
            "images": imgs
        })

    liked_by_me = post["liked_by_me"]
    saved_by_me = post["saved_by_me"]

    # OWNER REELS

    owner_id = post["user_id"]

    # OWNER REELS
    c.execute("""
        SELECT
            id,
            caption,
            video_path,
            thumbnail,
            views
        FROM reels
        WHERE user_id=?
        ORDER BY id DESC
    """, (owner_id,))

    owner_reels = []

    for r in c.fetchall():

        owner_reels.append({
            "id": r["id"],
            "caption": r["caption"],
            "video_path": r["video_path"],
            "thumbnail": r["thumbnail"],
            "views": r["views"]
        })

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

    # ADD THIS
    post["music_id"] = (
        audio["music_id"]
        if audio and audio["music_id"]
        else None
    )

    post["music_file"] = (
        "/static/music/uploads/" + audio["music_filename"]
        if audio and audio["music_filename"]
        else None
    )

    post["music_title"] = (
        audio["music_title"]
        if audio and audio["music_title"]
        else None
    )

    post["original_audio_id"] = (
        audio["original_audio_id"]
        if audio and audio["original_audio_id"]
        else None
    )

    post["original_audio_file"] = (
        audio["original_audio_file"]
        if audio and audio["original_audio_file"]
        else None
    )

    post["original_audio_title"] = (
        audio["original_audio_title"]
        if audio and audio["original_audio_title"]
        else None
    )

    post["audio_type"] = (
        "original"
        if audio and audio["original_audio_id"]
        else "music"
        if audio and audio["music_id"]
        else None
    )

    print("POST DICT BEFORE AUDIO:", dict(post))
    print("POST MUSIC ID:", post["music_id"] if "music_id" in post.keys() else "NO KEY")
    print("POST ORIGINAL AUDIO ID:", post["original_audio_id"] if "original_audio_id" in post.keys() else "NO KEY")
    print("========== VIEW POST AUDIO DEBUG ==========")
    print("POST ID:", post["id"])
    print("AUDIO ROW:", dict(audio) if audio else None)
    print("MUSIC FILE:", post["music_file"])
    print("MUSIC ID:", post["music_id"])
    print("ORIGINAL AUDIO FILE:", post["original_audio_file"])
    print("AUDIO TYPE:", post["audio_type"])
    print("===========================================")

    # Current user profile photo
    current_user_photo = "/static/default_dp.png"

    if "user_id" in session:
        c.execute(
            "SELECT photo FROM users WHERE id=?",
            (session["user_id"],)
        )

        row = c.fetchone()

        if row and row["photo"]:
            current_user_photo = row["photo"]

    conn.close()

    return render_template(
            "post_view.html",
            posts=posts,
            post=post,
            images=images,
            likes=likes,
            comments=comments,
            liked_by_me=liked_by_me,
            saved_by_me=saved_by_me,

            current_user=session.get("user_id"),
            current_user_photo=current_user_photo,

            music_file=post["music_file"],
            music_start=(
                audio["start_time"]
                if audio
                else 0
            ),
            music_end=(
                audio["end_time"]
                if audio
                else 30
            ),
            music_volume=(
                audio["music_volume"]
                if audio
                else 100
            ),
            owner_posts=owner_posts,
            owner_reels=owner_reels
        )

# ===============================
# ❤️ LIKE / UNLIKE FROM POST VIEW
# ===============================
@posts_bp.route("/like_toggle/<int:post_id>", methods=["POST"])
def like_toggle(post_id):

    if "user_id" not in session:
        return redirect(url_for("auth.login"))

    uid = session["user_id"]

    conn = sqlite3.connect("database.db")
    c = conn.cursor()

    # Get post owner
    c.execute("""
        SELECT user_id
        FROM posts
        WHERE id=?
    """, (post_id,))

    post_row = c.fetchone()

    if not post_row:
        conn.close()
        return redirect(f"/posts/{post_id}")

    post_owner_id = post_row[0]

    # Check existing like
    c.execute("""
        SELECT id
        FROM likes
        WHERE post_id=?
          AND username=?
    """, (post_id, uid))

    liked = c.fetchone()

    if liked:

        # UNLIKE
        c.execute("""
            DELETE FROM likes
            WHERE id=?
        """, (liked[0],))

    else:

        # LIKE
        c.execute("""
            INSERT INTO likes
            (
                post_id,
                username
            )
            VALUES (?, ?)
        """, (
            post_id,
            uid
        ))

        # 🔔 POST LIKE NOTIFICATION
        if post_owner_id != uid:

            meta = {
                "post_id": post_id
            }

            c.execute("""
                INSERT INTO notifications
                (
                    user_id,
                    actor_id,
                    type,
                    meta
                )
                VALUES (?, ?, ?, ?)
            """, (
                post_owner_id,
                uid,
                "post_like",
                json.dumps(meta)
            ))

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
    SELECT users.id,
           users.username,
           users.photo
    FROM follows
    JOIN users ON follows.follower_id = users.id
    WHERE follows.following_id=?
    ORDER BY users.username ASC
    """, (uid,))

    followers = [{
        "id": r["id"],
        "username": r["username"],
        "photo": r["photo"] or "/static/default_dp.png"
    } for r in c.fetchall()]

    conn.close()

    return {"ok": True, "followers": followers}


# ===============================
# 📤 SHARE POST TO USER
# ===============================
@posts_bp.route("/share_to_user", methods=["POST"])
def share_to_user():
    from socketio_init import socketio

    if "user_id" not in session:
        return {"ok": False, "error": "login required"}

    from_user = session["user_id"]

    data = request.get_json() or {}

    to_user_id = data.get("to_user_id")
    post_id = data.get("post_id")

    if not to_user_id or not post_id:
        return {"ok": False, "error": "missing data"}

    conn = sqlite3.connect("database.db")
    conn.row_factory = sqlite3.Row
    c = conn.cursor()

    # Check post exists
    c.execute(
        "SELECT id FROM posts WHERE id=?",
        (post_id,)
    )

    post = c.fetchone()

    if not post:
        conn.close()
        return {"ok": False, "error": "post not found"}

    # Find/create DM chat
    c.execute("""
        SELECT id
        FROM chats
        WHERE (user1=? AND user2=?)
           OR (user1=? AND user2=?)
    """, (from_user, to_user_id, to_user_id, from_user))

    chat = c.fetchone()

    if chat:
        chat_id = chat["id"]
    else:
        c.execute("""
            INSERT INTO chats(user1, user2)
            VALUES (?, ?)
        """, (from_user, to_user_id))

        chat_id = c.lastrowid

    # Special message format
    msg = f"__SHARED_POST__:{int(post_id)}"

    c.execute("""
        INSERT INTO messages
        (chat_id, sender_id, msg, attachment, created_at)
        VALUES (?, ?, ?, NULL, datetime('now'))
    """, (
        chat_id,
        from_user,
        msg
    ))

    message_id = c.lastrowid

    conn.commit()
    conn.close()

    # Real-time message if receiver is currently inside chat
    socketio.emit(
        "new_message",
        {
            "chat_id": chat_id,
            "message": {
                "id": message_id,
                "sender_id": from_user,
                "msg": msg,
                "attachment": None,
                "deleted": 0,
                "seen": 0,
                "created_at": datetime.utcnow().strftime(
                    "%Y-%m-%d %H:%M:%S"
                )
            }
        },
        room=f"chat_{chat_id}"
    )

    return {
        "ok": True,
        "chat_id": chat_id,
        "message_id": message_id
    }

    # ------------------------------------------------
    # FIND / CREATE EXISTING CHAT
    # ------------------------------------------------

    c.execute("""
        SELECT id
        FROM chats
        WHERE (user1=? AND user2=?)
           OR (user1=? AND user2=?)
        LIMIT 1
    """, (
        from_user,
        to_user_id,
        to_user_id,
        from_user
    ))

    chat = c.fetchone()

    if chat:
        chat_id = chat["id"]

    else:
        c.execute("""
            INSERT INTO chats(user1,user2)
            VALUES(?,?)
        """, (
            from_user,
            to_user_id
        ))

        conn.commit()
        chat_id = c.lastrowid

    # ------------------------------------------------
    # POST SHARE DATA
    # ------------------------------------------------

    import json

    attachment = json.dumps({
        "type": "post",
        "post_id": int(post_id)
    })

    # Small message shown if old client doesn't understand card
    msg = "📌 Shared a post"

    # ------------------------------------------------
    # INSERT INTO YOUR EXISTING MESSAGES TABLE
    # ------------------------------------------------

    c.execute("""
        INSERT INTO messages
        (
            chat_id,
            sender_id,
            msg,
            attachment,
            created_at
        )
        VALUES (
            ?, ?, ?, ?, datetime('now')
        )
    """, (
        chat_id,
        from_user,
        msg,
        attachment
    ))

    conn.commit()

    message_id = c.lastrowid

    # Get inserted message
    c.execute("""
        SELECT
            id,
            sender_id,
            msg,
            attachment,
            created_at,
            edited,
            deleted
        FROM messages
        WHERE id=?
    """, (message_id,))

    row = c.fetchone()

    conn.close()

    message = dict(row)

    message["seen"] = 0

    # ------------------------------------------------
    # REAL-TIME MESSAGE
    # ------------------------------------------------

    from socketio_init import socketio

    socketio.emit(
        "new_message",
        {
            "chat_id": chat_id,
            "message": message
        },
        room=f"chat_{chat_id}"
    )

    return jsonify({
        "ok": True,
        "chat_id": chat_id,
        "message_id": message_id
    })

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
############ comment ##################
############ POST COMMENT SYSTEM ##################

@posts_bp.route("/comments/<int:post_id>")
def comments_page(post_id):

    if "user_id" not in session:
        return redirect(url_for("auth.login"))

    return render_template(
        "post_comments.html",
        post_id=post_id,
        current_user=session["user_id"]
    )


@posts_bp.route("/comments_api/<int:post_id>")
def comments_api(post_id):

    conn = sqlite3.connect("database.db")
    conn.row_factory = sqlite3.Row
    c = conn.cursor()

    # -----------------------------
    # MAIN COMMENTS
    # -----------------------------
    c.execute("""
        SELECT
            comments.id,
            comments.user_id,
            comments.comment,
            comments.created_at,
            users.username,
            users.photo
        FROM comments
        JOIN users
            ON comments.user_id = users.id
        WHERE comments.post_id=?
          AND comments.reply_to IS NULL
        ORDER BY comments.id DESC
    """, (post_id,))

    main_comments = c.fetchall()

    comments = []

    for r in main_comments:

        # -------------------------
        # COMMENT LIKES
        # -------------------------
        c.execute("""
            SELECT COUNT(*)
            FROM reel_comment_likes
            WHERE comment_id=?
        """, (r["id"],))

        likes = c.fetchone()[0]

        liked = False

        if "user_id" in session:

            c.execute("""
                SELECT 1
                FROM reel_comment_likes
                WHERE comment_id=?
                  AND user_id=?
            """, (
                r["id"],
                session["user_id"]
            ))

            liked = c.fetchone() is not None

        # -------------------------
        # REPLIES
        # -------------------------
        c.execute("""
            SELECT
                comments.id,
                comments.user_id,
                comments.comment,
                comments.created_at,
                users.username,
                users.photo
            FROM comments
            JOIN users
                ON comments.user_id = users.id
            WHERE comments.post_id=?
              AND comments.reply_to=?
            ORDER BY comments.id ASC
        """, (
            post_id,
            r["id"]
        ))

        replies = []

        for rr in c.fetchall():

            c.execute("""
                SELECT COUNT(*)
                FROM reel_comment_likes
                WHERE comment_id=?
            """, (rr["id"],))

            reply_likes = c.fetchone()[0]

            reply_liked = False

            if "user_id" in session:

                c.execute("""
                    SELECT 1
                    FROM reel_comment_likes
                    WHERE comment_id=?
                      AND user_id=?
                """, (
                    rr["id"],
                    session["user_id"]
                ))

                reply_liked = c.fetchone() is not None

            replies.append({

                "id": rr["id"],

                "user_id": rr["user_id"],

                "username": rr["username"],

                "profile":
                    rr["photo"]
                    or "/static/default_dp.png",

                "text":
                    rr["comment"],

                "likes":
                    reply_likes,

                "liked":
                    reply_liked

            })

        comments.append({

            "id":
                r["id"],

            "user_id":
                r["user_id"],

            "username":
                r["username"],

            "profile":
                r["photo"]
                or "/static/default_dp.png",

            "text":
                r["comment"],

            "likes":
                likes,

            "liked":
                liked,

            "replies":
                replies

        })

    conn.close()

    return {
        "comments": comments
    }


# -----------------------------
# POST COMMENT / REPLY
# -----------------------------
@posts_bp.route(
    "/comment/<int:post_id>",
    methods=["POST"]
)
def post_comment(post_id):

    if "user_id" not in session:
        return {
            "ok": False,
            "error": "login required"
        }, 401

    uid = session["user_id"]

    text = request.form.get(
        "comment",
        ""
    ).strip()

    if not text:
        return {
            "ok": False,
            "error": "empty comment"
        }, 400

    reply_to = request.form.get("reply_to")

    if reply_to:
        try:
            reply_to = int(reply_to)
        except:
            reply_to = None

    conn = sqlite3.connect("database.db")
    c = conn.cursor()

    # --------------------------------
    # GET POST OWNER
    # --------------------------------
    c.execute("""
        SELECT user_id
        FROM posts
        WHERE id=?
    """, (post_id,))

    post_row = c.fetchone()

    if not post_row:
        conn.close()

        return {
            "ok": False,
            "error": "post not found"
        }, 404

    post_owner_id = post_row[0]

    # --------------------------------
    # REPLY PARENT VERIFY
    # --------------------------------
    parent_owner_id = None

    if reply_to:

        c.execute("""
            SELECT user_id
            FROM comments
            WHERE id=?
              AND post_id=?
        """, (
            reply_to,
            post_id
        ))

        parent = c.fetchone()

        if parent:

            parent_owner_id = parent[0]

        else:

            reply_to = None

    # --------------------------------
    # INSERT COMMENT / REPLY
    # --------------------------------
    c.execute("""
        INSERT INTO comments
        (
            post_id,
            user_id,
            comment,
            reply_to
        )
        VALUES (?, ?, ?, ?)
    """, (
        post_id,
        uid,
        text,
        reply_to
    ))

    comment_id = c.lastrowid

    # --------------------------------
    # 🔔 NOTIFICATION
    # --------------------------------

    # REPLY
    if reply_to is not None:

        # Reply ki notification parent comment
        # ke owner ko jayegi
        if parent_owner_id and parent_owner_id != uid:

            meta = {
                "post_id": post_id,
                "comment_id": comment_id,
                "parent_id": reply_to
            }

            c.execute("""
                INSERT INTO notifications
                (
                    user_id,
                    actor_id,
                    type,
                    meta
                )
                VALUES (?, ?, ?, ?)
            """, (
                parent_owner_id,
                uid,
                "post_reply",
                json.dumps(meta)
            ))

    # NORMAL COMMENT
    else:

        # Post owner ko notification
        # apne post par khud comment kare to nahi
        if post_owner_id != uid:

            meta = {
                "post_id": post_id,
                "comment_id": comment_id
            }

            c.execute("""
                INSERT INTO notifications
                (
                    user_id,
                    actor_id,
                    type,
                    meta
                )
                VALUES (?, ?, ?, ?)
            """, (
                post_owner_id,
                uid,
                "post_comment",
                json.dumps(meta)
            ))

    conn.commit()
    conn.close()

    return {
        "ok": True,
        "comment_id": comment_id
    }

# -----------------------------
# DELETE POST COMMENT
# -----------------------------
@posts_bp.route(
    "/comment_delete/<int:comment_id>",
    methods=["POST"]
)
def delete_post_comment(comment_id):

    if "user_id" not in session:
        return {
            "ok": False,
            "error": "login required"
        }, 401

    conn = sqlite3.connect("database.db")
    c = conn.cursor()

    c.execute("""
        SELECT user_id
        FROM comments
        WHERE id=?
    """, (comment_id,))

    row = c.fetchone()

    if not row:
        conn.close()

        return {
            "ok": False,
            "error": "comment not found"
        }, 404

    if row[0] != session["user_id"]:
        conn.close()

        return {
            "ok": False,
            "error": "not allowed"
        }, 403

    # Delete likes
    c.execute("""
        DELETE FROM reel_comment_likes
        WHERE comment_id=?
    """, (comment_id,))

    # Delete replies
    c.execute("""
        DELETE FROM comments
        WHERE reply_to=?
    """, (comment_id,))

    # Delete comment
    c.execute("""
        DELETE FROM comments
        WHERE id=?
    """, (comment_id,))

    conn.commit()
    conn.close()

    return {
        "ok": True
    }


# ===============================
# ❤️ LIKE / UNLIKE POST COMMENT
# ===============================
@posts_bp.route(
    "/comment_like/<int:comment_id>",
    methods=["POST"]
)
def post_comment_like(comment_id):

    if "user_id" not in session:
        return {
            "ok": False,
            "error": "login required"
        }

    uid = session.get("user_id")

    conn = sqlite3.connect("database.db")
    conn.row_factory = sqlite3.Row
    c = conn.cursor()

    # ==========================================
    # CHECK COMMENT
    # ==========================================
    c.execute("""
        SELECT
            id,
            user_id,
            post_id,
            reply_to
        FROM comments
        WHERE id=?
    """, (comment_id,))

    comment = c.fetchone()

    if not comment:
        conn.close()

        return {
            "ok": False,
            "error": "comment not found"
        }

    comment_owner_id = comment["user_id"]
    post_id = comment["post_id"]
    parent_id = comment["reply_to"]

    # ==========================================
    # CHECK EXISTING LIKE
    # ==========================================
    c.execute("""
        SELECT id
        FROM reel_comment_likes
        WHERE comment_id=?
          AND user_id=?
    """, (comment_id, uid))

    existing = c.fetchone()

    # ==========================================
    # ❤️ UNLIKE
    # ==========================================
    if existing:

        c.execute("""
            DELETE FROM reel_comment_likes
            WHERE comment_id=?
              AND user_id=?
        """, (
            comment_id,
            uid
        ))

        liked = False

    # ==========================================
    # ❤️ LIKE
    # ==========================================
    else:

        c.execute("""
            INSERT OR IGNORE INTO reel_comment_likes
            (
                comment_id,
                user_id
            )
            VALUES (?, ?)
        """, (
            comment_id,
            uid
        ))

        liked = True

        # ======================================
        # 🔔 COMMENT LIKE NOTIFICATION
        # ======================================

        # Khud ke comment ko like kare
        # to notification nahi jayegi
        if comment_owner_id != uid:

            meta = {
                "post_id": post_id,
                "comment_id": comment_id
            }

            # Agar ye reply hai
            if parent_id is not None:
                meta["parent_id"] = parent_id

            c.execute("""
                INSERT INTO notifications
                (
                    user_id,
                    actor_id,
                    type,
                    meta
                )
                VALUES (?, ?, ?, ?)
            """, (
                comment_owner_id,
                uid,
                "post_comment_like",
                json.dumps(meta)
            ))

    # ==========================================
    # GET TOTAL LIKES
    # ==========================================
    c.execute("""
        SELECT COUNT(*) AS total
        FROM reel_comment_likes
        WHERE comment_id=?
    """, (comment_id,))

    row = c.fetchone()

    likes = row["total"] if row else 0

    conn.commit()
    conn.close()

    return {
        "ok": True,
        "liked": liked,
        "likes": likes
    }

# ===============================
# 🖼️ SHARED POST THUMBNAIL
# ===============================
@posts_bp.route("/shared_post/<int:post_id>")
def shared_post_info(post_id):
    current_uid = session.get("user_id", 0)

    conn = sqlite3.connect("database.db")
    conn.row_factory = sqlite3.Row

    try:
        row = conn.execute("""
            SELECT
                pi.image_path,
                u.id AS owner_id,
                COALESCE(u.is_private, 0) AS is_private,
                COALESCE(u.suspended, 0) AS suspended,
                COALESCE(u.banned, 0) AS banned
            FROM posts p
            JOIN users u ON u.id = p.user_id
            LEFT JOIN post_images pi ON pi.post_id = p.id
            WHERE p.id = ?
            ORDER BY pi.id ASC
            LIMIT 1
        """, (post_id,)).fetchone()

        if not row:
            return {"ok": False}, 404

        if row["suspended"] or row["banned"]:
            return {"ok": False}, 404

        # Private account: owner or approved follower only.
        if row["is_private"] and current_uid != row["owner_id"]:
            allowed = conn.execute("""
                SELECT 1
                FROM follows
                WHERE follower_id = ?
                  AND following_id = ?
                LIMIT 1
            """, (current_uid, row["owner_id"])).fetchone()

            if not allowed:
                return {"ok": False}, 404

        image = row["image_path"]

        if not image:
            image = "/static/default_post.png"
        else:
            filename = image.rsplit("/", 1)[-1]
            extension = (
                "." + filename.rsplit(".", 1)[-1].lower()
                if "." in filename else ""
            )

            video_extensions = {
                ".mp4", ".webm", ".mov", ".mkv", ".avi", ".m4v"
            }

            if extension in video_extensions:
                stem = filename.rsplit(".", 1)[0]
                image = f"/static/uploads/posts/thumbs/{stem}_thumb.jpg"
            elif image.startswith("static/"):
                image = "/" + image
            elif not image.startswith("/"):
                image = "/static/uploads/" + image

        return {
            "ok": True,
            "image": image
        }

    finally:
        conn.close()

# ===============================
# 🎵 ORIGINAL AUDIO PAGE
# ===============================
@posts_bp.route("/original-audio/<int:audio_id>")
def original_audio_page(audio_id):

    conn = sqlite3.connect("database.db")
    conn.row_factory = sqlite3.Row

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
        WHERE oa.id = ?
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
