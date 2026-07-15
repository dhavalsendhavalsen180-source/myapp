import eventlet
eventlet.monkey_patch()

from flask_socketio import SocketIO

socketio = SocketIO(
    cors_allowed_origins="*",
    manage_session=True,
    async_mode="eventlet",
    logger=True,
    engineio_logger=True
)
