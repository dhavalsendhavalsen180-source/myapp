from flask_socketio import emit, join_room, leave_room
from flask import session, Blueprint, render_template, request
from socketio_init import socketio
from datetime import datetime
from threading import Timer
import sqlite3

call_bp = Blueprint("call_bp", __name__, url_prefix="/call")


@call_bp.route("/<int:chat_id>")
def call_page(chat_id):
    call_type = request.args.get("type", "audio")

    # ✔ caller flag detect
    caller = request.args.get("caller") == "1"
    conn = sqlite3.connect("database.db")
    conn.row_factory = sqlite3.Row
    c = conn.cursor()
    me = session.get("user_id")
    c.execute("SELECT user1,user2 FROM chats WHERE id=?", (chat_id,))
    chat = c.fetchone()
    other = chat["user2"] if chat["user1"] == me else chat["user1"]
    c.execute("SELECT username, photo FROM users WHERE id=?", (other,))
    u = c.fetchone()
    username = u["username"] if u else "Unknown"
    photo = u["photo"] if u and u["photo"] else "/static/default_dp.png"
    conn.close()

    return render_template(
        "call.html",
        chat_id=chat_id,
        call_type=call_type,
        caller=caller,
        caller_photo=photo,
        caller_name=username
    )

# ================= CALL STATE ================
active_calls = {}

def get_call(chat_id):
    return active_calls.get(chat_id)

def set_call(chat_id, state):
    active_calls[chat_id] = state

def clear_call(chat_id):
    active_calls.pop(chat_id, None)


# ================= GET RECEIVER =================
def get_receiver(chat_id, me):
    conn = sqlite3.connect("database.db")
    c = conn.cursor()

    c.execute(
        "SELECT user1, user2 FROM chats WHERE id=?",
        (chat_id,)
    )

    row = c.fetchone()
    conn.close()

    if row is None:
        return None

    user1, user2 = row

    if user1 == me:
        return user2
    return user1


def call_timeout(chat_id):
    call = get_call(chat_id)

    if not call:
        return

    if call["status"] != "ringing":
        return

    clear_call(chat_id)

    socketio.emit(
        "call_timeout",
        {
            "chat_id": chat_id
        },
        room=f"call_{chat_id}"
    )

# ================= JOIN CHAT ROOM ================
@socketio.on("join_call_chat")
def join_call_chat(data):
    print("JOIN CALL:", data)
    chat_id = data.get("chat_id")
    if not chat_id:
        return

    join_room(f"call_{chat_id}")
    emit("joined_chat", {"chat_id": chat_id})

# ================= CALL REQUEST =================
@socketio.on("call_request")
def call_request(data):
    print("CALL REQUEST:", data)

    me = session.get("user_id")
    chat_id = data.get("chat_id")
    call_type = data.get("type")

    if not me or not chat_id:
        return

    # Receiver nikaalo chats table se
    receiver = get_receiver(chat_id, me)
    print("ME =", me)
    print("RECEIVER =", receiver)
    print("CHAT_ID =", chat_id)

    if not receiver:
        return

    # Block new call if one already active
    if get_call(chat_id):
        emit("call_busy", {"chat_id": chat_id})
        return

    call_id = int(datetime.utcnow().timestamp())

    # Save active call
    set_call(chat_id, {
        "call_id": call_id,
        "caller": me,
        "receiver": receiver,
        "status": "ringing",
        "type": call_type,
        "started_at": datetime.utcnow().isoformat()
    })

    # Auto timeout after 30 sec
    Timer(30, call_timeout, args=[chat_id]).start()

    print("SENDING incoming_call TO:", f"user_{receiver}")

    socketio.emit(
        "incoming_call",
        {
            "chat_id": chat_id,
            "from": me,
            "type": call_type
        },
        room=f"user_{receiver}",
        include_self=False
    )

    print("incoming_call SENT")
# ================= ACCEPT =================
@socketio.on("call_accept")
def call_accept(data):
    print("CALL ACCEPT:", data)
    me = session.get("user_id")
    chat_id = data.get("chat_id")

    call = get_call(chat_id)
    if not call:
        return

    # Update active call
    call["status"] = "active"
    set_call(chat_id, call)

    # Update database
    conn = sqlite3.connect("database.db")
    conn.row_factory = sqlite3.Row
    c = conn.cursor()
    me = session.get("user_id")
    c.execute("SELECT user1,user2 FROM chats WHERE id=?", (chat_id,))
    chat = c.fetchone()
    other = chat["user2"] if chat["user1"] == me else chat["user1"]
    c.execute("SELECT username, photo FROM users WHERE id=?", (other,))
    u = c.fetchone()
    username = u["username"] if u else "Unknown"
    photo = u["photo"] if u and u["photo"] else "/static/default_dp.png"
    conn.close()

    socketio.emit(
        "call_accepted",
        {
            "chat_id": chat_id,
            "by": me
        },
        room=f"call_{chat_id}"
    )

# ================= REJECT =================
@socketio.on("call_reject")
def call_reject(data):
    me = session.get("user_id")
    chat_id = data.get("chat_id")

    call = get_call(chat_id)
    if not call:
        return

    conn = sqlite3.connect("database.db")
    conn.row_factory = sqlite3.Row
    c = conn.cursor()
    me = session.get("user_id")
    c.execute("SELECT user1,user2 FROM chats WHERE id=?", (chat_id,))
    chat = c.fetchone()
    other = chat["user2"] if chat["user1"] == me else chat["user1"]
    c.execute("SELECT username, photo FROM users WHERE id=?", (other,))
    u = c.fetchone()
    username = u["username"] if u else "Unknown"
    photo = u["photo"] if u and u["photo"] else "/static/default_dp.png"
    conn.close()

    clear_call(chat_id)

    socketio.emit(
        "call_rejected",
        {
            "chat_id": chat_id,
            "by": me
        },
        room=f"call_{chat_id}"
    )

# ================= END =================
@socketio.on("call_ended")
def call_ended(data):
    me = session.get("user_id")
    chat_id = data.get("chat_id")

    call = get_call(chat_id)
    if not call:
        return

    # Update database
    conn = sqlite3.connect("database.db")
    conn.row_factory = sqlite3.Row
    c = conn.cursor()
    me = session.get("user_id")
    c.execute("SELECT user1,user2 FROM chats WHERE id=?", (chat_id,))
    chat = c.fetchone()
    other = chat["user2"] if chat["user1"] == me else chat["user1"]
    c.execute("SELECT username, photo FROM users WHERE id=?", (other,))
    u = c.fetchone()
    username = u["username"] if u else "Unknown"
    photo = u["photo"] if u and u["photo"] else "/static/default_dp.png"
    conn.close()

    clear_call(chat_id)

    socketio.emit(
        "call_ended",
        {
            "chat_id": chat_id,
            "by": me
        },
        room=f"call_{chat_id}"
    )

# ================= SIGNALING =================
@socketio.on("webrtc_offer")
def webrtc_offer(data):
    print("WEBRTC OFFER:", data)
    chat_id = data.get("chat_id")
    socketio.emit("webrtc_offer", data, room=f"call_{chat_id}", include_self=False)


@socketio.on("webrtc_answer")
def webrtc_answer(data):
    print("WEBRTC ANSWER:", data)
    chat_id = data.get("chat_id")
    socketio.emit("webrtc_answer", data, room=f"call_{chat_id}", include_self=False)


@socketio.on("webrtc_ice")
def webrtc_ice(data):
    print("WEBRTC ICE:", data)
    chat_id = data.get("chat_id")
    socketio.emit("webrtc_ice", data, room=f"call_{chat_id}", include_self=False)
