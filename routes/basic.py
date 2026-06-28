from flask import Blueprint, render_template, redirect, session

basic_bp = Blueprint("basic", __name__)

@basic_bp.route("/")
def splash():
    return render_template("splash.html")

@basic_bp.route("/home")
def home():
    # Agar user login hai to feed
    if session.get("user_id"):
        return redirect("/posts/feed")

    # Nahi to login page
    return redirect("/auth/login")
