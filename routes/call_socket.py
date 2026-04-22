from flask_socketio import emit, join_room, leave_room
from flask import session, Blueprint, render_template, request
from socketio_init import socketio
from datetime import datetime

call_bp = Blueprint("call_bp", __name__, url_prefix="/call")


@call_bp.route("/<int:chat_id>")
def call_page(chat_id):
    call_type = request.args.get("type", "audio")

    # ✔ caller flag detect
    caller = request.args.get("caller") == "1"

    return render_template(
        "call.html",
        chat_id=chat_id,
        call_type=call_type,
        caller=caller
    )

# ================= CALL STATE ================
active_calls = {}

def get_call(chat_id):
    return active_calls.get(chat_id)

def set_call(chat_id, state):
    active_calls[chat_id] = state

def clear_call(chat_id):
    active_calls.pop(chat_id, None)


# ================= JOIN CHAT ROOM ================
@socketio.on("join_chat")
def join_chat(data):
    chat_id = data.get("chat_id")
    if not chat_id:
        return
    join_room(f"chat_{chat_id}")
    emit("joined_chat", {"chat_id": chat_id})

# ================= CALL REQUEST =================
@socketio.on("call_request")
def call_request(data):
    me = session.get("user_id")
    chat_id = data.get("chat_id")
    call_type = data.get("type")

    if not me or not chat_id:
        return

    # block new call if one already active
    if get_call(chat_id):
        emit("call_busy", {"chat_id": chat_id})
        return

    set_call(chat_id, {
        "caller": me,
        "status": "ringing",
        "type": call_type,
        "started_at": datetime.utcnow().isoformat()
    })

    socketio.emit(
        "incoming_call",
        {"chat_id": chat_id, "from": me, "type": call_type},
        room=f"chat_{chat_id}",
        include_self=False
    )


# ================= ACCEPT =================
@socketio.on("call_accept")
def call_accept(data):
    me = session.get("user_id")
    chat_id = data.get("chat_id")

    call = get_call(chat_id)
    if not call:
        return

    call["status"] = "active"
    set_call(chat_id, call)

    socketio.emit(
        "call_accepted",
        {"chat_id": chat_id, "by": me},
        room=f"chat_{chat_id}"
    )


# ================= REJECT =================
@socketio.on("call_reject")
def call_reject(data):
    me = session.get("user_id")
    chat_id = data.get("chat_id")

    clear_call(chat_id)

    socketio.emit(
        "call_rejected",
        {"chat_id": chat_id, "by": me},
        room=f"chat_{chat_id}"
    )


# ================= END =================
@socketio.on("call_ended")
def call_ended(data):
    me = session.get("user_id")
    chat_id = data.get("chat_id")

    clear_call(chat_id)

    socketio.emit(
        "call_ended",
        {"chat_id": chat_id, "by": me},
        room=f"chat_{chat_id}"
    )


# ================= SIGNALING =================
@socketio.on("webrtc_offer")
def webrtc_offer(data):
    chat_id = data.get("chat_id")
    socketio.emit("webrtc_offer", data, room=f"chat_{chat_id}", include_self=False)


@socketio.on("webrtc_answer")
def webrtc_answer(data):
    chat_id = data.get("chat_id")
    socketio.emit("webrtc_answer", data, room=f"chat_{chat_id}", include_self=False)


@socketio.on("webrtc_ice")
def webrtc_ice(data):
    chat_id = data.get("chat_id")
    socketio.emit("webrtc_ice", data, room=f"chat_{chat_id}", include_self=False)
