from flask import Flask
from flask_cors import CORS
from routes.basic import basic_bp
from routes.auth import auth_bp
from routes.posts import posts_bp
import auth_backend

app = Flask(__name__)
CORS(app)

app.secret_key = "kuch_strong_secret_key" 

# database initialize
auth_backend.init_users_db()
auth_backend.init_posts_db()
auth_backend.init_posts_extras()

# blueprints register karo
app.register_blueprint(basic_bp)
app.register_blueprint(auth_bp, url_prefix="/auth")
app.register_blueprint(posts_bp, url_prefix="/posts")


if __name__ == "__main__":
    import os
    port = int(os.environ.get("PORT", 5000))
    app.run(host="0.0.0.0", port=port)
