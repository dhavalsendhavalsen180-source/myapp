import sqlite3
import os
import json
import time
from flask import Blueprint, render_template, request, redirect, session, url_for, jsonify, flash, send_from_directory
from werkzeug.utils import secure_filename

stories_bp = Blueprint("stories", __name__, url_prefix="/stories")

# ---------------- CONFIG ----------------
STORY_FOLDER = os.path.join("static", "stories")
DATA_DIR = "data"
STORY_FILE = os.path.join(DATA_DIR, "stories.json")
REPLIES_FILE = os.path.join(DATA_DIR, "story_replies.json")

ALLOWED = {
    # Images
    "jpg", "jpeg", "png", "gif", "webp",
    "bmp", "tiff", "tif",
    "heic", "heif",
    "avif",

    # Videos
    "mp4", "webm", "mov",
    "m4v", "3gp", "3g2",
    "avi", "mkv", "mpeg",
    "mpg", "wmv"
}
EXPIRE_SECONDS = 24 * 60 * 60

os.makedirs(STORY_FOLDER, exist_ok=True)
os.makedirs(DATA_DIR, exist_ok=True)


# ---------------- HELPERS ----------------
def now_ts():
    return int(time.time())


def read_json(path):
    if not os.path.exists(path):
        return []
    try:
        with open(path, "r", encoding="utf-8") as f:
            return json.load(f)
    except:
        return []


def write_json(path, data):
    with open(path, "w", encoding="utf-8") as f:
        json.dump(data, f, indent=2, ensure_ascii=False)


def load_stories():
    return read_json(STORY_FILE)


def save_stories(data):
    write_json(STORY_FILE, data)


def load_replies():
    return read_json(REPLIES_FILE)


def save_replies(data):
    write_json(REPLIES_FILE, data)


# ---------------- CLEANUP ----------------
def cleanup_expired():
    stories = load_stories()
    now = now_ts()

    kept = []

    for s in stories:
        if now - int(s.get("timestamp", 0)) < EXPIRE_SECONDS:
            kept.append(s)
        else:
            fn = s.get("filename")
            if fn:
                try:
                    os.remove(os.path.join(STORY_FOLDER, fn))
                except:
                    pass

    save_stories(kept)


# ---------------- STORY UPLOAD ----------------
@stories_bp.route("/add", methods=["POST"])
def add_story():
    if "user_id" not in session:
        return redirect("/auth/login")

    file = request.files.get("story")
    if not file or file.filename == "":
        return redirect("/")

    ext = file.filename.rsplit(".", 1)[-1].lower()
    if ext not in ALLOWED:
        return "File not allowed", 400

    filename = f"{session['user_id']}_{now_ts()}_{secure_filename(file.filename)}"
    path = os.path.join(STORY_FOLDER, filename)
    file.save(path)

    stories = load_stories()

    stories.append({
        "id": len(stories) + 1,
        "user_id": str(session["user_id"]),
        "filename": filename,
        "timestamp": now_ts(),
        "viewers": [],
        "likes": [],
        "reactions": {}
    })

    save_stories(stories)

    print("STORY SAVED:", filename)

    print("STORY SAVED:", stories)
    return redirect("/")


# ---------------- GROUPED STORIES (INS CORE) ----------------
@stories_bp.route("/api/groups")
def groups():
    cleanup_expired()
    stories = load_stories()

    grouped = {}

    for s in stories:
        uid = s["user_id"]

        if uid not in grouped:
            grouped[uid] = {
                "user_id": uid,
                "stories": []
            }

        grouped[uid]["stories"].append({
            "id": s["id"],
            "filename": s["filename"],
            "timestamp": s["timestamp"]
        })

    return jsonify(list(grouped.values()))


# ---------------- VIEW STORIES ----------------
@stories_bp.route("/view/<username>")
def view(username):
    cleanup_expired()

    stories = load_stories()

    user_stories = [
        s for s in stories
        if str(s.get("user_id")) == str(username)
    ]

    user_stories.sort(key=lambda x: x.get("timestamp", 0))

    # NO STORY
    if not user_stories:

        # own profile -> upload page
        if str(session.get("user_id")) == str(username):
            return redirect("/stories/create")

        # other user -> back feed
        return redirect("/posts/feed")

    # mark seen
    if "user_id" in session:
        for s in user_stories:
            if session["user_id"] not in s.get("viewers", []):
                s.setdefault("viewers", []).append(session["user_id"])

        save_stories(stories)

    replies = [
        r for r in load_replies()
        if r.get("to_user") == username
    ]

    # USER INFO
    conn = sqlite3.connect("database.db")
    conn.row_factory = sqlite3.Row
    c = conn.cursor()

    c.execute(
        "SELECT id, username, photo FROM users WHERE id=?",
        (username,)
    )

    user = c.fetchone()
    conn.close()

    display_name = username
    profile_photo = "/static/default_dp.png"

    if user:
        display_name = user["username"]

        if user["photo"]:
            profile_photo = user["photo"]

    for s in user_stories:
         s.setdefault("likes", [])

    story_users = []

    for item in get_storybar_for_user(session.get("user_id")):
        story_users.append(str(item["user_id"]))

    if str(username) not in story_users:
        story_users.insert(0, str(username))

    return render_template(
        "story_view.html",
        stories=user_stories,
        owner=display_name,
        owner_id=username,
        replies=replies,
        profile_photo=profile_photo,
        current_user=session.get("user_id"),
        story_users=story_users
    )

# ---------------- REACT ----------------
@stories_bp.route("/api/react", methods=["POST"])
def react():

    if "user_id" not in session:
        return jsonify({"ok": False}), 401

    data = request.get_json()
    story_id = data.get("story_id")

    stories = load_stories()

    for s in stories:

        if s["id"] == story_id:

            s.setdefault("likes", [])

            uid = str(session["user_id"])

            if uid in s["likes"]:
                s["likes"].remove(uid)
                liked = False
            else:
                s["likes"].append(uid)
                liked = True

            save_stories(stories)

            return jsonify({
                "ok": True,
                "liked": liked
            })

    return jsonify({"ok": False}), 404

# ---------------- REPLY ----------------
@stories_bp.route("/api/reply", methods=["POST"])
def reply():
    if "user_id" not in session:
        return jsonify({"ok": False}), 401

    data = request.get_json()

    replies = load_replies()

    replies.append({
        "from": session["user_id"],
        "to_user": data.get("to_user"),
        "story_id": data.get("story_id"),
        "text": data.get("text"),
        "timestamp": now_ts()
    })

    save_replies(replies)

    return jsonify({"ok": True})


# ---------------- MEDIA ----------------
@stories_bp.route("/media/<filename>")
def media(filename):
    return send_from_directory(STORY_FOLDER, filename)

def load_stories_for_feed():
    cleanup_expired()
    stories = load_stories()

    return [
        {
            "id": s.get("id"),
            "user_id": s.get("user_id"),
            "filename": s.get("filename"),
            "timestamp": s.get("timestamp"),
            "viewers": s.get("viewers", [])
        }
        for s in stories
    ]

    bar = []


    grouped = {}

    for s in stories:
        uid = s.get("user_id")
        if not uid:
            continue

        if uid not in grouped or s.get("timestamp", 0) > grouped[uid].get("timestamp", 0):
            grouped[uid] = s

    bar = []

    for uid, s in grouped.items():

        # ❌ skip own story
        if str(uid) == str(current_user):
            continue

        bar.append({
            "user_id": uid,
            "last_img": "/stories/media/" + s.get("filename"),
            "seen": str(current_user) in [str(x) for x in (s.get("viewers") or [])]
        })

    return bar

def get_storybar_for_user(current_user):
    cleanup_expired()
    stories = load_stories()

    conn = sqlite3.connect("database.db")
    conn.row_factory = sqlite3.Row
    c = conn.cursor()

    grouped = {}

    for s in stories:
        uid = s.get("user_id")
        if not uid:
            continue

        if uid not in grouped or s.get("timestamp", 0) > grouped[uid].get("timestamp", 0):
            grouped[uid] = s

    bar = []

    for uid, s in grouped.items():

        if str(uid) == str(current_user):
            continue

        c.execute(
            "SELECT username, photo FROM users WHERE id=?",
            (uid,)
        )

        u = c.fetchone()

        username = str(uid)
        photo = "/static/default_dp.png"

        if u:
            username = u["username"]
            if u["photo"]:
                photo = u["photo"]

        bar.append({
            "user_id": uid,
            "username": username,
            "last_img": photo,
            "seen": str(current_user) in [str(x) for x in (s.get("viewers") or [])]
        })

    conn.close()
    return bar

######################################################
@stories_bp.route("/api/delete", methods=["POST"])
def delete_story():
    if "user_id" not in session:
        return jsonify({"ok": False}), 401

    data = request.get_json()
    story_id = data.get("story_id")

    stories = load_stories()

    new_stories = []
    deleted = False

    for s in stories:
        if s["id"] == story_id and s["user_id"] == str(session["user_id"]):
            deleted = True
            try:
                os.remove(os.path.join(STORY_FOLDER, s["filename"]))
            except:
                pass
            continue

        new_stories.append(s)

    save_stories(new_stories)

    return jsonify({"ok": deleted})
#################( activity ) ##############
@stories_bp.route("/activity/<int:story_id>")
def story_activity(story_id):

    if "user_id" not in session:
        return redirect("/auth/login")

    stories = load_stories()

    story = None

    for s in stories:
        if s["id"] == story_id:
            story = s
            break

    if not story:
        return "Story not found"

    if story["user_id"] != str(session["user_id"]):
        return "Unauthorized", 403

    conn = sqlite3.connect("database.db")
    conn.row_factory = sqlite3.Row
    c = conn.cursor()

    viewers = []
    likes = []

    for uid in story.get("viewers", []):

        c.execute(
            "SELECT id, username, photo FROM users WHERE id=?",
            (str(uid),)
        )

        u = c.fetchone()

        if u:

            viewers.append({
                "id": u["id"],
                "id": uid,
                "username": u["username"],
                "photo": u["photo"] or "/static/default_dp.png"
            })

    for uid in story.get("likes", []):

        c.execute(
            "SELECT id, username, photo FROM users WHERE id=?",
            (str(uid),)
        )

        u = c.fetchone()

        if u:
            likes.append({
                "id": u["id"],
                "username": u["username"],
                "photo": u["photo"] or "/static/default_dp.png"
            })

    # remove duplicates
    liked_ids = [str(x["id"]) for x in likes]

    viewers = [
        v for v in viewers
        if str(v["id"]) not in liked_ids
    ]

    conn.close()

    return render_template(
        "story_activity.html",
        story=story,
        viewers=viewers,
        likes=likes
    )

###################################
@stories_bp.route("/api/reply", methods=["POST"])
def reply_story():
    if "user_id" not in session:
        return jsonify({"ok": False}), 401

    data = request.get_json()

    replies = load_replies()

    replies.append({
        "from": session["user_id"],
        "to_user": data.get("to_user"),
        "story_id": data.get("story_id"),
        "text": data.get("text"),
        "timestamp": now_ts()
    })

    save_replies(replies)

    return jsonify({"ok": True})


##################################
@stories_bp.route("/create")
def create_story_page():
    return render_template("story_create.html")

################( activity_count )#################
@stories_bp.route("/activity_count/<int:story_id>")
def activity_count(story_id):

    stories = load_stories()

    for s in stories:
        if s["id"] == story_id:
            return jsonify({
                "likes": len(s.get("likes", [])),
                "views": len(s.get("viewers", []))
            })

    return jsonify({"likes":0,"views":0})
