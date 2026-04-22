from app import app
from flask import send_from_directory, Response
import mimetypes

# Manifest.json fix
@app.route("/manifest.json")
def manifest():
    return send_from_directory(".", "manifest.json", mimetype="application/json")

# Service worker correct MIME type
@app.route("/sw.js")
def service_worker():
    return Response(
        send_from_directory(".", "sw.js").get_data(),
        mimetype="application/javascript"
    )

# Static files routing
@app.route("/static/<path:path>")
def send_static(path):
    return send_from_directory("static", path)
