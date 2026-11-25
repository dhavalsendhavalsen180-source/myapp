from flask import session, request
from flask_socketio import emit, join_room
from socketio_init import socketio
from threading import Lock
import time

active_users = {}
presence_lock = Lock()

OFFLINE_AFTER = 50
cleanup_started = False


def get_user_id():
    value = session.get("user_id")

    try:
        return int(value)
    except (TypeError, ValueError):
        return None


def broadcast_status(user_id, status):
    socketio.emit(
        "global_presence",
        {
            "user_id": int(user_id),
            "status": status
        },
        room="presence_watchers"
    )


def cleanup_loop():
    while True:
        socketio.sleep(5)
        now = time.time()
        offline_users = []

        with presence_lock:
            for user_id, sockets in list(active_users.items()):
                expired = [
                    sid for sid, last in sockets.items()
                    if now - last > OFFLINE_AFTER
                ]

                for sid in expired:
                    sockets.pop(sid, None)

                if not sockets:
                    active_users.pop(user_id, None)
                    offline_users.append(user_id)

        for user_id in offline_users:
            broadcast_status(user_id, "offline")


@socketio.on("presence_start")
def presence_start():
    global cleanup_started

    user_id = get_user_id()
    if user_id is None:
        return

    sid = request.sid
    now = time.time()

    with presence_lock:
        sockets = active_users.setdefault(user_id, {})
        was_active = bool(sockets)
        sockets[sid] = now

        if not cleanup_started:
            cleanup_started = True
            socketio.start_background_task(cleanup_loop)

    if not was_active:
        broadcast_status(user_id, "online")

    emit("presence_started", {
        "user_id": user_id,
        "status": "online"
    })


@socketio.on("presence_heartbeat")
def presence_heartbeat():
    user_id = get_user_id()
    if user_id is None:
        return

    with presence_lock:
        sockets = active_users.get(user_id)

        if sockets is not None and request.sid in sockets:
            sockets[request.sid] = time.time()


@socketio.on("presence_stop")
def presence_stop():
    user_id = get_user_id()
    if user_id is None:
        return

    with presence_lock:
        sockets = active_users.get(user_id, {})
        sockets.pop(request.sid, None)

        still_active = bool(sockets)

        if not still_active:
            active_users.pop(user_id, None)

    if not still_active:
        broadcast_status(user_id, "offline")


@socketio.on("presence_watch")
def presence_watch(data):
    if get_user_id() is None:
        return

    join_room("presence_watchers")

    if not isinstance(data, dict):
        return

    try:
        target_id = int(data.get("user_id"))
    except (TypeError, ValueError):
        return

    now = time.time()

    with presence_lock:
        sockets = active_users.get(target_id, {})

        online = any(
            now - last <= OFFLINE_AFTER
            for last in sockets.values()
        )

    emit("global_presence", {
        "user_id": target_id,
        "status": "online" if online else "offline"
    })
