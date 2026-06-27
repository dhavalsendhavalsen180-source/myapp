from flask import Blueprint, render_template, request, redirect, url_for, flash, session
import sqlite3

from werkzeug.security import generate_password_hash, check_password_hash

from authlib.integrations.flask_client import OAuth
from flask import current_app
import os

auth_bp = Blueprint("auth", __name__, url_prefix="/auth")

oauth = OAuth()

google = oauth.register(
name="google",
client_id=os.getenv("GOOGLE_CLIENT_ID"),
client_secret=os.getenv("GOOGLE_CLIENT_SECRET"),
server_metadata_url="https://accounts.google.com/.well-known/openid-configuration",
client_kwargs={
"scope": "openid email profile"
}
)

# ---------------- Register ----------------
@auth_bp.route("/register", methods=["GET", "POST"])
def register():
    if request.method == "POST":
        username = request.form.get("username", "").strip()
        password = request.form.get("password", "").strip()
        email = request.form.get("email", "").strip()
        phone = request.form.get("phone", "").strip()
        dob = request.form.get("dob", "").strip()

        if not username or not password or not phone or not dob:
            flash("All fields are required!", "error")
            return redirect(url_for("auth.register"))

        if len(password) < 8:
            flash("Password must be at least 8 characters!", "error")
            return redirect(url_for("auth.register"))

        conn = sqlite3.connect("database.db")
        c = conn.cursor()

        # duplicate check
        c.execute("SELECT id FROM users WHERE username=?", (username,))
        if c.fetchone():
            conn.close()
            flash("Username already exists!", "error")
            return redirect(url_for("auth.register"))

        # insert new user_id
        hashed_password = generate_password_hash(password)
        c.execute(
            "INSERT INTO users (username, password, email, phone, dob) VALUES (?, ?, ?, ?, ?)",
            (username, hashed_password, email, phone, dob)
        )
        conn.commit()
        conn.close()

        flash("Registration successful!", "success")
        return redirect(url_for("auth.login"))

    return render_template("register.html")


# ---------------- Login ----------------

# ---------------- Login ----------------
@auth_bp.route("/login", methods=["GET", "POST"])
def login():
    if request.method == "POST":
        username = request.form.get("username", "").strip()
        password = request.form.get("password", "").strip()

        conn = sqlite3.connect("database.db")
        c = conn.cursor()

        # Sabse pehle ID + password fetch karo
        c.execute("SELECT id, password FROM users WHERE username=?", (username,))
        row = c.fetchone()
        conn.close()

        if not row:
            flash("Invalid username or password!", "error")
            return render_template("login.html")

        user_id = row[0]
        stored_pass = row[1]

        # Plain text compare
        if check_password_hash(stored_pass, password):
            session["user_id"] = user_id
            flash("Login successful!", "success")
            return redirect(url_for("posts.feed"))

        else:
            flash("Invalid username or password!", "error")
            return render_template("login.html")

    return render_template("login.html")

################# live #######################
@auth_bp.route("/check_username")
def check_username():
    username = request.args.get("username", "").strip()

    conn = sqlite3.connect("database.db")
    c = conn.cursor()

    c.execute(
        "SELECT id FROM users WHERE lower(username)=lower(?)",
        (username,)
    )

    exists = c.fetchone() is not None
    conn.close()

    return {"available": not exists}


###############################################
###############################################
@auth_bp.route("/signup", methods=["GET", "POST"])
def signup():

  if request.method == "POST":

    phone = request.form.get("phone", "").strip()

    session["signup_phone"] = phone

    return redirect(url_for("auth.verify"))

  return render_template("signup_phone.html")

##############################################
@auth_bp.route("/verify", methods=["GET", "POST"])
def verify():

  if request.method == "POST":

    code = request.form.get("code")

    if code == "123456":
        return redirect(url_for("auth.register"))

    flash("Invalid code", "error")

  return render_template("verify.html")


##########################################
@auth_bp.route("/google")
def google_login():
    redirect_uri = url_for("auth.google_callback", _external=True)
    return google.authorize_redirect(redirect_uri)


@auth_bp.route("/google/callback")
def google_callback():
    token = google.authorize_access_token()
    user_info = token.get("userinfo")

    if not user_info:
        flash("Google login failed", "error")
        return redirect(url_for("auth.login"))

    email = user_info["email"]
    username = email.split("@")[0]

    conn = sqlite3.connect("database.db")
    c = conn.cursor()

    c.execute("SELECT id FROM users WHERE email=?", (email,))
    user = c.fetchone()

    if not user:
        c.execute(
            "INSERT INTO users (username, email, password, phone, dob, google_id) VALUES (?, ?, ?, ?, ?, ?)",
            (
                username,
                email,
                "",
                "",
                "",
                user_info["sub"]
            )
        )
        conn.commit()

        c.execute("SELECT id FROM users WHERE email=?", (email,))
        user = c.fetchone()

    conn.close()

    session["user_id"] = user[0]

    return redirect(url_for("posts.feed"))
