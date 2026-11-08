from flask import Blueprint, render_template, redirect, session

tab_shell_bp = Blueprint("tab_shell", __name__)

@tab_shell_bp.route("/app")
def app_shell():
    if not session.get("user_id"):
        return redirect("/auth/login")

    return render_template(
        "app_shell.html",
        current_user=session["user_id"]
    )
