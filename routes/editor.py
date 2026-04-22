import os
import base64
from flask import Blueprint, render_template, request, session, redirect, url_for, flash, current_app

editor_bp = Blueprint("editor", __name__, url_prefix="/editor")

UPLOAD_DIR = "static/edits"
os.makedirs(UPLOAD_DIR, exist_ok=True)

@editor_bp.route("/", methods=["GET"])
def editor_page():
    # optional: require login
    # if "user_id" not in session: return redirect(url_for("auth.login"))
    return render_template("editor.html")

@editor_bp.route("/save", methods=["POST"])
def editor_save():
    data_url = request.form.get("dataUrl")
    if not data_url:
        return {"ok": False, "error": "no_data"}, 400

    # data_url: data:image/png;base64,AAAA...
    header, encoded = data_url.split(",", 1)
    ext = "png"
    if "jpeg" in header or "jpg" in header:
        ext = "jpg"

    try:
        data = base64.b64decode(encoded)
    except Exception as e:
        return {"ok": False, "error": "decode_failed"}, 400

    fname = f"edit_{os.urandom(6).hex()}.{ext}"
    path = os.path.join(UPLOAD_DIR, fname)
    with open(path, "wb") as f:
        f.write(data)

    # you can also store path in DB against user_id if you want
    return {"ok": True, "path": f"/{path}"}
