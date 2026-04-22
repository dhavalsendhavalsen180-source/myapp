from flask import Flask
from flask_cors import CORS
from flask_socketio import SocketIO

from routes.basic import basic_bp
from routes.auth import auth_bp
from routes.posts import posts_bp
from routes.social import social_bp
from routes.profile import profile_bp
from routes.explore import explore_bp
from routes.reels import reels_bp, init_reels_db
from routes.create import create_bp
from routes.editor import editor_bp
from routes.stories import stories_bp
from routes.messages_socket import messages_bp
from routes.call_socket import call_bp
import auth_backend
import routes.call_socket

app = Flask(__name__)
CORS(app)
app.secret_key = "kuch_strong_secret_key"

# DATABASE INIT
auth_backend.init_users_db()
auth_backend.init_posts_db()
auth_backend.init_posts_extras()
auth_backend.init_notifications_db()
init_reels_db()

# SOCKET.IO INIT (Option A)
socketio = SocketIO(app, cors_allowed_origins="*", async_mode="eventlet")

# BLUEPRINTS
app.register_blueprint(basic_bp)
app.register_blueprint(auth_bp, url_prefix="/auth")
app.register_blueprint(posts_bp, url_prefix="/posts")
app.register_blueprint(social_bp, url_prefix="/social")
app.register_blueprint(profile_bp)
app.register_blueprint(explore_bp)
app.register_blueprint(reels_bp)
app.register_blueprint(create_bp)
app.register_blueprint(editor_bp)
app.register_blueprint(stories_bp, url_prefix="/stories")
app.register_blueprint(messages_bp)
app.register_blueprint(call_bp)

if __name__ == "__main__":
    socketio.run(app, host="0.0.0.0", port=5000, debug=True)
