# routes/stories.py
import os
import json
import time
from flask import (
    Blueprint, render_template, request, redirect, session,
    url_for, jsonify, flash, send_from_directory
)
from werkzeug.utils import secure_filename

# Blueprint
stories_bp = Blueprint("stories", __name__, url_prefix="/stories")

# Config
STORY_FOLDER = os.path.join("static", "stories")
DATA_DIR = "data"
STORY_FILE = os.path.join(DATA_DIR, "stories.json")
REPLIES_FILE = os.path.join(DATA_DIR, "story_replies.json")
ALLOWED = {"png", "jpg", "jpeg", "gif", "mp4", "webm"}
EXPIRE_SECONDS = 24 * 60 * 60  # 24 hours

# Ensure folders exist
os.makedirs(STORY_FOLDER, exist_ok=True)
os.makedirs(DATA_DIR, exist_ok=True)


# -----------------------
# helpers: timestamps + json io
# -----------------------
def now_ts():
    return int(time.time())


def _read_json(path):
    if not os.path.exists(path):
        return []
    try:
        with open(path, "r", encoding="utf-8") as f:
            return json.load(f)
    except Exception:
        return []


def _write_json(path, data):
    with open(path, "w", encoding="utf-8") as f:
        json.dump(data, f, indent=2, ensure_ascii=False)


# -----------------------
# core storage helpers
# -----------------------
def load_stories():
    """Return raw stories list (list of dicts)."""
    return _read_json(STORY_FILE)


def save_stories(data):
    _write_json(STORY_FILE, data)


def load_replies():
    return _read_json(REPLIES_FILE)


def save_replies(data):
    _write_json(REPLIES_FILE, data)


# -----------------------
# cleanup expired files
# -----------------------
def cleanup_expired():
    """
    Remove stories older than EXPIRE_SECONDS and delete files from disk.
    Safe to call often.
    """
    stories = load_stories()
    kept = []
    now = time.time()
    changed = False
    for s in stories:
        t = s.get("timestamp") or s.get("time") or 0
        if now - t < EXPIRE_SECONDS:
            kept.append(s)
        else:
            # delete stored media_path if exists
            fn = s.get("filename") or s.get("media_path")
            if fn:
                try:
                    path = os.path.join(STORY_FOLDER, fn)
                    if os.path.exists(path):
                        os.remove(path)
                except Exception:
                    pass
            changed = True
    if changed:
        save_stories(kept)
    else:
        # still rewrite to normalize if needed
        save_stories(kept)


# -----------------------
# feed helpers (used by posts blueprint)
# - load_stories_for_feed() -> list of story entries for feed processing
# - get_storybar_for_user(current_user) -> list for story bar (latest per user_id)
# -----------------------
def load_stories_for_feed():
    """
    Returns minimal story dicts (id,user_id,filename,timestamp,viewers)
    for consumption by feed route.
    """
    cleanup_expired()
    data = load_stories()
    out = []
    for s in data:
        out.append({
            "id": s.get("id"),
            "user_id": s.get("user_id"),
            "filename": s.get("filename") or s.get("media_path"),
            "timestamp": s.get("timestamp") or s.get("time"),
            "viewers": s.get("viewers", [])
        })
    return out


def get_storybar_for_user(current_user):
    """
    Produce story bar data: one entry per user_id (latest story),
    with seen flag (True if current_user in viewers of latest story).
    """
    cleanup_expired()
    data = load_stories()
    # group by user_id and pick latest by timestamp
    grouped = {}
    for s in data:
        user_id = s.get("user_id")
        if not user_id:
            continue
        t = s.get("timestamp") or s.get("time") or 0
        if user_id not in grouped or t > (grouped[user_id].get("timestamp") or grouped[user_id].get("time") or 0):
            grouped[user_id] = s

    bar = []
    # sort users so bar is stable (optional: by latest time descending)
    users_sorted = sorted(grouped.items(), key=lambda kv: (kv[1].get("timestamp") or kv[1].get("time") or 0), reverse=True)
    for user_id, last in users_sorted:
        fn = last.get("filename") or last.get("media_path")
        bar.append({
            "user_id": user_id,
            "last_img": url_for("static", filename=f"stories/{fn}"),
            "seen": (current_user in last.get("viewers", [])) if current_user else False,
            "timestamp": last.get("timestamp") or last.get("time") or 0
        })
    return bar


# -----------------------
# ROUTES
# -----------------------

# optional GET uploader page (template must exist)

@stories_bp.route("/create", methods=["GET"])
def create_get():
    """
    Show uploader UI. Template name expected: 'create_story.html'.
    Provide music list from static/music (optional).
    """
    if "user_id" not in session:
        return redirect(url_for("auth.login"))

    music_list = []
    music_dir = os.path.join("static", "music")

    if os.path.isdir(music_dir):
        for f in os.listdir(music_dir):
            if f.lower().endswith((".mp3", ".ogg", ".m4a")):
                music_list.append(f)

    return render_template("upload.html", music_list=music_list)

# upload endpoint (POST) — form submit
@stories_bp.route("/add", methods=["POST"])
def add_story():
    if "user_id" not in session:
        flash("Login required to add story", "error")
        return redirect(url_for("auth.login"))

    media_path = request.files.get("story")
    if not media_path or media_path.filename == "":
        flash("No media_path selected", "error")
        return redirect(url_for("posts.feed"))

    ext = media_path.filename.rsplit(".", 1)[-1].lower()
    if ext not in ALLOWED:
        flash("File type not allowed", "error")
        return redirect(url_for("posts.feed"))

    filename = f"{session.get('user_id')}_{now_ts()}_{secure_filename(media_path.filename)}"
    save_path = os.path.join(STORY_FOLDER, filename)
    media_path.save(save_path)

    # read existing, append new
    stories = load_stories()
    new_id = (max([s.get("id", 0) for s in stories]) + 1) if stories else 1
    entry = {
        "id": new_id,
        "user_id": session.get("user_id"),
        "filename": filename,
        "timestamp": now_ts(),
        "viewers": [],
        "reactions": {},     # reaction -> count or list, keep simple
        "meta": {
            "text": request.form.get("text", "") or "",
            "text_bg": request.form.get("text_bg", "#000000"),
            "music": request.form.get("music", "") or ""
        }
    }
    stories.append(entry)
    save_stories(stories)
    flash("Story uploaded", "success")
    return redirect(url_for("posts.feed"))


# fullscreen viewer for a user_id's stories
@stories_bp.route("/view/<string:username>", methods=["GET"])
def view_stories(username):
    cleanup_expired()
    stories = load_stories()
    user_stories = [s for s in stories if s.get("user_id") == username]
    user_stories = sorted(user_stories, key=lambda x: x.get("timestamp") or x.get("time") or 0)

    # mark current session user_id as viewer for each story
    changed = False
    if "user_id" in session:
        cur = session.get("user_id")
        for s in user_stories:
            viewers = s.setdefault("viewers", [])
            if cur not in viewers:
                viewers.append(cur)
                changed = True
    if changed:
        save_stories(stories)

    # convert entries to template-friendly shape (fields used by story_view.html)
    # our template expects: stories = list of dicts with id, filename, meta, timestamp
    tmpl_stories = []
    for s in user_stories:
        tmpl_stories.append({
            "id": s.get("id"),
            "filename": s.get("filename"),
            "meta": s.get("meta", {}),
            "timestamp": s.get("timestamp")
        })

    # replies for this owner (optional)
    replies = [r for r in load_replies() if r.get("to_user") == username]
    return render_template("story_view.html", stories=tmpl_stories, owner=username, replies=replies)


# Simple API: react to a story (JSON)
@stories_bp.route("/api/react", methods=["POST"])
def api_react():
    if "user_id" not in session:
        return jsonify({"ok": False, "error": "login"}), 401
    data = request.get_json() or {}
    story_id = data.get("story_id")
    reaction = data.get("reaction")
    if not story_id or not reaction:
        return jsonify({"ok": False}), 400

    stories = load_stories()
    for s in stories:
        if int(s.get("id")) == int(story_id):
            # store reaction counts (simple)
            reactions = s.setdefault("reactions", {})
            reactions[reaction] = reactions.get(reaction, 0) + 1
            save_stories(stories)
            return jsonify({"ok": True, "reactions": reactions})
    return jsonify({"ok": False}), 404


# Simple API: reply to story owner (save in replies media_path)
@stories_bp.route("/api/reply", methods=["POST"])
def api_reply():
    if "user_id" not in session:
        return jsonify({"ok": False, "error": "login"}), 401
    data = request.get_json() or {}
    to_user = data.get("to_user")
    story_id = data.get("story_id")
    text = (data.get("text") or "").strip()
    if not to_user or not text:
        return jsonify({"ok": False}), 400

    replies = load_replies()
    replies.append({
        "from": session.get("user_id"),
        "to_user": to_user,
        "story_id": story_id,
        "text": text,
        "timestamp": now_ts()
    })
    save_replies(replies)
    return jsonify({"ok": True})


# API: list stories grouped (helpful for frontend fetch)
@stories_bp.route("/api/list", methods=["GET"])
def api_list():
    cleanup_expired()
    stories = load_stories()
    # pick latest per user_id
    grouped = {}
    for s in stories:
        u = s.get("user_id")
        if not u:
            continue
        t = s.get("timestamp") or 0
        if u not in grouped or t > (grouped[u].get("timestamp") or 0):
            grouped[u] = s
    out = []
    for user_id, s in grouped.items():
        out.append({
            "user_id": user_id,
            "last_img": url_for("static", filename=f"stories/{s.get('filename')}"),
            "seen": (session.get("user_id") in s.get("viewers", [])) if session.get("user_id") else False,
            "timestamp": s.get("timestamp")
        })
    return jsonify({"ok": True, "stories": out})


# legacy POST react/reply endpoints (form posts) kept for compatibility
@stories_bp.route("/react", methods=["POST"])
def react_form():
    if "user_id" not in session:
        return "Login required", 401
    user_id = request.form.get("user_id")
    emoji = request.form.get("emoji")
    if not user_id or not emoji:
        return "bad", 400
    stories = load_stories()
    found = False
    for s in stories:
        if s.get("user_id") == user_id:
            s.setdefault("reactions", {})
            s["reactions"][emoji] = s["reactions"].get(emoji, 0) + 1
            found = True
            break
    if found:
        save_stories(stories)
        return "ok"
    return "not found", 404


@stories_bp.route("/reply", methods=["POST"])
def reply_form():
    if "user_id" not in session:
        return "Login required", 401
    to = request.form.get("to")
    msg = request.form.get("msg")
    if not to or not msg:
        return "bad", 400
    replies = load_replies()
    replies.append({
        "from": session.get("user_id"),
        "to_user": to,
        "text": msg,
        "timestamp": now_ts()
    })
    save_replies(replies)
    return "sent"


# Serve raw story media_path (optional fallback)
@stories_bp.route("/media_path/<path:filename>")
def serve_file(filename):
    # Safety: only serve from STORY_FOLDER
    return send_from_directory(STORY_FOLDER, filename, as_attachment=False)


# quick debug endpoint: show stored JSON (for debug only; remove in prod)
@stories_bp.route("/_debug/list_raw")
def debug_list_raw():
    return jsonify(load_stories())


