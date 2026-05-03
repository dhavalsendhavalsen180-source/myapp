active_calls = {}
import sqlite3, os
from flask import Blueprint, render_template, session, redirect, request, jsonify, current_app
from flask_socketio import emit, join_room, leave_room
from datetime import datetime, timedelta
from threading import Timer
from socketio_init import socketio

messages_bp = Blueprint("messages_bp", __name__, url_prefix="/messages")

# ----------------- DB -----------------
def get_db():
    db = os.path.join(current_app.root_path, "database.db")
    conn = sqlite3.connect(db, check_same_thread=False)
    conn.row_factory = sqlite3.Row
    return conn

# ----------------- HELPERS -----------------
def find_or_create_chat(a, b):
    conn = get_db(); c = conn.cursor()
    c.execute("""SELECT id, locked, lock_pin FROM chats
                 WHERE (user1=? AND user2=?) OR (user1=? AND user2=?)""",
              (a,b,b,a))
    r = c.fetchone()
    if r:
        cid = r["id"]
    else:
        c.execute("INSERT INTO chats(user1,user2) VALUES(?,?)",(a,b))
        conn.commit()
        cid = c.lastrowid
    conn.close()
    return cid

def remove_expired_messages_for_chat(chat_id):
    conn = get_db()
    c = conn.cursor()

    now_str = datetime.utcnow().strftime("%Y-%m-%d %H:%M:%S")

    c.execute(
        "SELECT id FROM messages WHERE chat_id=? AND expires_at IS NOT NULL AND expires_at<=?",
        (chat_id, now_str)
    )
    rows = c.fetchall()

    for r in rows:
        mid = r["id"]
        c.execute(
            "UPDATE messages SET deleted=1, msg='' WHERE id=?",
            (mid,)
        )
        socketio.emit(
            "message_deleted",
            {"chat_id": chat_id, "message_id": mid},
            room=f"chat_{chat_id}"
        )

    conn.commit()
    conn.close()


def user_is_ghost(user_id):
    conn = get_db(); c = conn.cursor()
    c.execute("SELECT ghost_mode FROM users WHERE id=?", (user_id,))
    r = c.fetchone(); conn.close()
    return bool(r and r["ghost_mode"])

presence_cache = {}   # {user_id: active_count}
user_sockets = {}     # {user_id: set(socket_ids)}
typing_timers = {}    # {(chat_id, user_id): Timer}

def set_last_seen(user_id):
    conn = get_db(); c = conn.cursor()
    c.execute("UPDATE users SET last_seen=datetime('now') WHERE id=?", (user_id,))
    conn.commit(); conn.close()

def typing_stop(chat_id, user_id):
    socketio.emit("typing_stop", {"chat_id": chat_id, "user_id": user_id}, room=f"chat_{chat_id}", include_self=False)
    typing_timers.pop((chat_id, user_id), None)

def is_ghost(user_id):
    return user_is_ghost(user_id)

# ----------------- ROUTES -----------------
@messages_bp.route("/")
def inbox():
    if "user_id" not in session:
        return redirect("/auth/login")
    me = session["user_id"]
    conn = get_db(); c = conn.cursor()
    c.execute("""
        SELECT ch.id AS chat_id,
               CASE WHEN ch.user1=? THEN ch.user2 ELSE ch.user1 END AS other_id,
               u.username, u.photo,
               m.msg AS last_msg, m.created_at AS last_time,
               (SELECT COUNT(*) FROM messages ms
                 LEFT JOIN message_receipts mr ON mr.message_id=ms.id AND mr.user_id=?
                 WHERE ms.chat_id=ch.id AND mr.id IS NULL AND ms.sender_id!=?
               ) AS unread_count
        FROM chats ch
        LEFT JOIN users u ON u.id = CASE WHEN ch.user1=? THEN ch.user2 ELSE ch.user1 END
        LEFT JOIN messages m ON m.chat_id=ch.id AND m.id = (SELECT id FROM messages WHERE chat_id=ch.id ORDER BY id DESC LIMIT 1)
        WHERE ch.user1=? OR ch.user2=?
        GROUP BY ch.id
        ORDER BY last_time DESC
    """, (me, me, me, me, me, me))
    rows = c.fetchall(); conn.close()
    inbox = []
    for r in rows:
        inbox.append({
            "chat_id": r["chat_id"],
            "other_id": r["other_id"],
            "username": r["username"],
            "photo": r["photo"] or "/static/profile/default_dp.png",
            "last_msg": r["last_msg"] or "",
            "last_time": r["last_time"] or "",
            "unread": r["unread_count"] or 0
        })
    return render_template("messages_inbox.html", chats=inbox)

@messages_bp.route("/chat/<int:other_id>")
def chat_page(other_id):
    if "user_id" not in session:
        return redirect("/auth/login")

    me = session["user_id"]
    chat_id = find_or_create_chat(me, other_id)

    conn = get_db()
    c = conn.cursor()

    c.execute("SELECT id, username, photo FROM users WHERE id=?", (other_id,))
    u = c.fetchone()
    other = {
        "id": u["id"],
        "username": u["username"],
        "photo": u["photo"] or "/static/profile/default_dp.png"
    }

    remove_expired_messages_for_chat(chat_id)

    c.execute("""
SELECT 
    m.id,
    m.sender_id,
    m.msg,
    m.edited,
    m.deleted,
    m.created_at,
    m.view_once,
    m.expires_at,
    m.attachment,
    CASE 
        WHEN EXISTS (
            SELECT 1 FROM message_receipts r
            WHERE r.message_id = m.id AND r.user_id = ?
        ) THEN 1 ELSE 0
    END AS seen
FROM messages m
WHERE m.chat_id=? AND m.deleted=0
ORDER BY m.id ASC
""", (me, chat_id))

    msgs = [dict(x) for x in c.fetchall()]
    conn.close()

    return render_template(
        "messages_chat.html",
        me=me,
        other=other,
        chat_id=chat_id,
        messages=msgs
    )

# ----------------- SOCKET EVENTS -----------------

@socketio.on("connect")
def on_connect():
    me = session.get("user_id")
    print("SOCKET CONNECTED:", me)

@socketio.on("join_chat")
def join_chat(data):
    chat_id = data.get("chat_id")
    me = session.get("user_id")
    if not me or not chat_id:
        return

    sid = request.sid
    user_sockets.setdefault(me, set()).add(sid)
    presence_cache[me] = presence_cache.get(me, 0) + 1

    room = f"chat_{chat_id}"
    join_room(room)

    remove_expired_messages_for_chat(chat_id)

    if not is_ghost(me):
        conn = get_db(); c = conn.cursor()
        c.execute("""
            INSERT INTO message_receipts(message_id,user_id,seen_at)
            SELECT id, ?, datetime('now') FROM messages
            WHERE chat_id=? AND sender_id!=? AND id NOT IN (
                SELECT message_id FROM message_receipts WHERE user_id=?
            )
        """, (me, chat_id, me, me))
        conn.commit(); conn.close()

        socketio.emit("messages_seen", {"chat_id": chat_id, "user_id": me}, room=room, include_self=False)
        socketio.emit("presence", {"chat_id": chat_id, "user_id": me, "status": "online"}, room=room, include_self=False)

@socketio.on("leave")
def leave_chat(data):
    chat_id = data.get("chat_id"); me = session.get("user_id")
    if not me or not chat_id: return
    room = f"chat_{chat_id}"
    leave_room(room)
    presence_cache[me] = max(0, presence_cache.get(me,0)-1)
    if presence_cache[me]==0 and not is_ghost(me):
        set_last_seen(me)
        socketio.emit("presence", {"chat_id": chat_id, "user_id": me, "status":"offline", "last_seen": datetime.utcnow().isoformat()}, room=room, include_self=False)

@socketio.on("typing")
def typing_event(data):
    chat_id = data.get("chat_id"); me = session.get("user_id")
    if not me or not chat_id or is_ghost(me): return
    socketio.emit("typing", {"chat_id": chat_id, "user_id": me}, room=f"chat_{chat_id}", include_self=False)
    key = (chat_id, me)
    if key in typing_timers: typing_timers[key].cancel()
    timer = Timer(3.5, typing_stop, args=[chat_id, me])
    typing_timers[key] = timer; timer.start()

#--------------------------- send -----------------------#
@socketio.on("send_message")
def send_message(data):
    me = session.get("user_id")
    chat_id = data.get("chat_id")

    text = (data.get("msg") or "").strip()
    attachment = data.get("attachment_url")

    if not me or not chat_id or (not text and not attachment):
        return

    conn = get_db()
    c = conn.cursor()

    c.execute("""
        INSERT INTO messages
        (chat_id, sender_id, msg, attachment, created_at)
        VALUES (?, ?, ?, ?, datetime('now'))
    """, (chat_id, me, text, attachment))

    conn.commit()
    mid = c.lastrowid

    c.execute("""
        SELECT id, sender_id, msg, attachment, created_at
        FROM messages WHERE id=?
    """, (mid,))
    r = c.fetchone()
    conn.close()

    m = {
        "id": r["id"],
        "sender_id": r["sender_id"],
        "msg": r["msg"],
        "attachment": r["attachment"],
        "deleted": 0,
        "seen": 0,
        "created_at": r["created_at"]
    }

    socketio.emit(
        "new_message",
        {"chat_id": chat_id, "message": m},
        room=f"chat_{chat_id}"
    )

#--------------------------- seen -----------------------#
@socketio.on("seen")
def seen_messages(data):
    me = session.get("user_id")
    chat_id = data.get("chat_id")
    if not me or not chat_id:
        return

    conn = get_db()
    c = conn.cursor()

    # mark unseen messages as seen
    c.execute("""
        INSERT INTO message_receipts(message_id, user_id, seen_at)
        SELECT m.id, ?, datetime('now')
        FROM messages m
        LEFT JOIN message_receipts r
          ON r.message_id = m.id AND r.user_id = ?
        WHERE m.chat_id = ?
          AND m.sender_id != ?
          AND r.id IS NULL
    """, (me, me, chat_id, me))

    conn.commit()
    conn.close()

    socketio.emit(
        "messages_seen",
        {"chat_id": chat_id, "user_id": me},
        room=f"chat_{chat_id}",
        include_self=False
    )

#--------------------------- viewed -----------------------#
@socketio.on("view_once_viewed")
def view_once(data):
    me=session.get("user_id"); mid=data.get("message_id"); chat_id=data.get("chat_id")
    if not me or not mid: return
    conn=get_db(); c=conn.cursor()
    c.execute("SELECT view_once FROM messages WHERE id=?", (mid,))
    r=c.fetchone()
    if not r or r["view_once"]!=1: conn.close(); return
    c.execute("INSERT INTO message_receipts(message_id,user_id,seen_at,view_once_seen) VALUES(?,?,datetime('now'),1)", (mid, me))
    c.execute("UPDATE messages SET deleted=1, msg='' WHERE id=?", (mid,))
    conn.commit(); conn.close()
    socketio.emit("view_once_viewed", {"chat_id": chat_id, "message_id": mid, "user_id": me}, room=f"chat_{chat_id}")
    socketio.emit("message_deleted", {"chat_id": chat_id, "message_id": mid}, room=f"chat_{chat_id}")

#--------------------------- message_edit -----------------------#

@socketio.on("message_edit")
def edit_message(data):
    me=session.get("user_id"); mid=data.get("message_id"); new_text=(data.get("new_text") or "").strip(); chat_id=data.get("chat_id")
    if not new_text: emit("error", {"error":"empty"}); return
    conn=get_db(); c=conn.cursor()
    c.execute("SELECT sender_id FROM messages WHERE id=?", (mid,))
    r=c.fetchone(); 
    if not r or r["sender_id"]!=me: conn.close(); return
    c.execute("UPDATE messages SET msg=?, edited=1 WHERE id=?", (new_text, mid))
    conn.commit()
    c.execute("SELECT * FROM messages WHERE id=?", (mid,))
    m=dict(c.fetchone()); conn.close()
    socketio.emit("message_edited", {"chat_id": chat_id, "message": m}, room=f"chat_{chat_id}")

#--------------------------- message_dilet -----------------------#
@socketio.on("message_delete")
def delete_message(data):
    me=session.get("user_id"); mid=data.get("message_id"); chat_id=data.get("chat_id")
    conn=get_db(); c=conn.cursor(); c.execute("SELECT sender_id FROM messages WHERE id=?", (mid,))
    r=c.fetchone()
    if not r or r["sender_id"]!=me: conn.close(); return
    c.execute("UPDATE messages SET deleted=1, msg='' WHERE id=?", (mid,)); conn.commit(); conn.close()
    socketio.emit("message_deleted", {"chat_id": chat_id, "message_id": mid}, room=f"chat_{chat_id}")

#--------------------------- lock_chat -----------------------#
@socketio.on("lock_chat")
def lock_chat(data):
    me=session.get("user_id"); chat_id=data.get("chat_id"); pin=data.get("pin")
    if not me or not chat_id or not pin: return
    conn=get_db(); c=conn.cursor()
    c.execute("UPDATE chats SET locked=1, lock_pin=? WHERE id=?", (pin, chat_id)); conn.commit(); conn.close()
    socketio.emit("chat_locked", {"chat_id": chat_id}, room=f"chat_{chat_id}")

#--------------------------- unlock_chat -----------------------#
@socketio.on("unlock_chat")
def unlock_chat(data):
    me=session.get("user_id"); chat_id=data.get("chat_id"); pin=data.get("pin")
    if not me or not chat_id or not pin: return
    conn=get_db(); c=conn.cursor()
    c.execute("SELECT lock_pin FROM chats WHERE id=?", (chat_id,)); r=c.fetchone()
    if not r: conn.close(); return
    if r["lock_pin"]==pin:
        c.execute("UPDATE chats SET locked=0 WHERE id=?", (chat_id,)); conn.commit(); conn.close()
        emit("chat_unlocked", {"chat_id": chat_id})
    else: conn.close(); emit("chat_unlock_failed", {"chat_id": chat_id})

#--------------------------- ghost_mode -----------------------#
@socketio.on("set_ghost_mode")
def set_ghost(data):
    me=session.get("user_id"); 
    if not me: return
    val=1 if int(data.get("ghost",0))==1 else 0
    conn=get_db(); c=conn.cursor(); c.execute("UPDATE users SET ghost_mode=? WHERE id=?", (val, me)); conn.commit(); conn.close()
    emit("ghost_mode_set", {"ghost": val})

#--------------------------- disconnect -----------------------#
@socketio.on("disconnect")
def disconnect_handler():
    me=session.get("user_id"); sid=request.sid
    if not me: return
    sockets=user_sockets.get(me,set())
    if sid in sockets: sockets.remove(sid)
    if sockets: user_sockets[me]=sockets; return
    else: user_sockets.pop(me,None)
    rooms=list(socketio.server.rooms(sid))
    for room in rooms:
        leave_room(room)
        chat_id=None
        if room.startswith("chat_"):
            try: chat_id=int(room.split("_")[1])
            except: pass
        if chat_id:
            set_last_seen(me)
            if not is_ghost(me):
                emit("presence", {"chat_id": chat_id, "user_id": me, "status":"offline", "last_seen": datetime.utcnow().isoformat()}, room=room, include_self=False)
