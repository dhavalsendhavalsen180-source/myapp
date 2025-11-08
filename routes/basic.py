from flask import Blueprint, render_template, request, redirect
import auth_backend

basic_bp = Blueprint("basic", __name__)

@basic_bp.route("/")
def splash():
    return render_template("splash.html")

@basic_bp.route("/home")
def home():
    token = request.cookies.get("token")
    user, code = auth_backend.verify(token)
    if code != 200:
        return redirect("/auth/login")
    # Login ke baad sidha feed
    return redirect("/posts/feed")
