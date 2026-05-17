import os
import json
import time
from flask import (
    Blueprint, render_template, request, redirect, session,
    url_for, jsonify, flash, send_from_directory
)
from werkzeug.utils import secure_filename

stories_bp = Blueprint("stories", __name__, url_prefix="/stories")

# ---------------- CONFIG ----------------
STORY_FOLDER = os.path.join("static", "stories")
DATA_DIR = "data"
STORY_FILE = os.path.join(DATA_DIR, "stories.json")
REPLIES_FILE = os.path.join(DATA_DIR, "story_replies.json")

ALLOWED = {"png", "jpg", "jpeg", "gif", "mp4", "webm"}
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
        "user_id": session["user_id"],
        "filename": filename,
        "timestamp": now_ts(),
        "viewers": [],
        "reactions": {}
    })

    save_stories(stories)

    return redirect("/")


# ---------------- GROUPED STORIES (INSTAGRAM CORE) ----------------
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
        if s["user_id"] == username
    ]

    user_stories.sort(key=lambda x: x["timestamp"])

    # mark seen
    if "user_id" in session:
        for s in user_stories:
            if session["user_id"] not in s["viewers"]:
                s["viewers"].append(session["user_id"])

        save_stories(stories)

    replies = [
        r for r in load_replies()
        if r.get("to_user") == username
    ]

    return render_template(
        "story_view.html",
        stories=user_stories,
        owner=username,
        replies=replies
    )


# ---------------- REACT ----------------
@stories_bp.route("/api/react", methods=["POST"])
def react():
    if "user_id" not in session:
        return jsonify({"ok": False}), 401

    data = request.get_json()

    story_id = data.get("story_id")
    reaction = data.get("reaction")

    stories = load_stories()

    for s in stories:
        if s["id"] == story_id:
            s.setdefault("reactions", {})
            s["reactions"][reaction] = s["reactions"].get(reaction, 0) + 1
            save_stories(stories)
            return jsonify({"ok": True})

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

def load_stories_for_feed():
    cleanup_expired()
    stories = load_stories()
    return [{"id": s.get("id"), "user_id": s.get("user_id"), "filename": s.get("filename"), "timestamp": s.get("timestamp"), "viewers": s.get("viewers", [])} for s in stories]


# ---------------- INSTAGRAM STORY BAR (FIX) ----------------
def get_storybar_for_user(current_user):
    cleanup_expired()
    stories = load_stories()

    grouped = {}

    for s in stories:
        uid = s.get("user_id")
        if not uid:
            continue

        if uid not in grouped or s.get("timestamp", 0) > grouped[uid].get("timestamp", 0):
            grouped[uid] = s

    bar = []

    for uid, s in grouped.items():
        bar.append({
            "user_id": uid,
            "last_img": "/static/stories/" + s.get("filename"),
            "seen": current_user in (s.get("viewers") or []),
            "timestamp": s.get("timestamp")
        })

    return bar
