from flask import Blueprint, render_template, request, redirect, url_for, flash, session
import sqlite3

from werkzeug.security import generate_password_hash, check_password_hash
from datetime import datetime, timedelta
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
@auth_bp.route("/register")
def register():
    return redirect(url_for("auth.register_username"))
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
########################################
# ==========================
# Instagram Style Signup Flow
# ==========================

@auth_bp.route("/register/username", methods=["GET", "POST"])
def register_username():

    if request.method == "POST":
        username = request.form.get("username", "").strip()

        if len(username) < 3:
            flash("Username must be at least 3 characters", "error")
            return redirect(url_for("auth.register_username"))

        conn = sqlite3.connect("database.db")
        c = conn.cursor()

        c.execute("SELECT id FROM users WHERE lower(username)=lower(?)", (username,))
        exists = c.fetchone()

        conn.close()

        if exists:
            flash("Username already taken", "error")
            return redirect(url_for("auth.register_username"))

        session["signup_username"] = username

        return redirect(url_for("auth.register_password"))

    return render_template("register_username.html")


@auth_bp.route("/register/password", methods=["GET", "POST"])
def register_password():

    if "signup_username" not in session:
        return redirect(url_for("auth.register_username"))

    if request.method == "POST":

        password = request.form.get("password", "").strip()

        if len(password) < 8:
            flash("Password must be at least 8 characters", "error")
            return redirect(url_for("auth.register_password"))

        session["signup_password"] = password

        return redirect(url_for("auth.register_dob"))

    return render_template("register_password.html")


@auth_bp.route("/register/dob", methods=["GET", "POST"])
def register_dob():

    if "signup_password" not in session:
        return redirect(url_for("auth.register_username"))

    if request.method == "POST":

        day = int(request.form["day"])
        month = int(request.form["month"])
        year = int(request.form["year"])

        try:
            birth_date = datetime(year, month, day).date()

            today = datetime.today().date()

            # Minimum age = 1 year
            if birth_date > today - timedelta(days=365):
                flash("Age must be at least 1 year.", "error")
                return redirect(url_for("auth.register_dob"))

            session["signup_dob"] = birth_date.strftime("%Y-%m-%d")

            return redirect(url_for("auth.register_verify"))

        except ValueError:
            flash("Invalid date.", "error")
            return redirect(url_for("auth.register_dob"))

    return render_template("register_dob.html")

##########################################################
@auth_bp.route("/register/verify", methods=["GET", "POST"])
def register_verify():

    if "signup_dob" not in session:
        return redirect(url_for("auth.register_username"))

    if request.method == "POST":

        phone = request.form.get("phone", "").strip()
        email = request.form.get("email", "").strip()

        username = session["signup_username"]
        password = session["signup_password"]
        dob = session["signup_dob"]

        # Google signup ho to Google email use karo
        final_email = email if email else session.get("google_email", "")
        google_id = session.get("google_id", None)

        hashed = generate_password_hash(password)

        conn = sqlite3.connect("database.db")
        c = conn.cursor()

        # Username ya Email pehle se exist karta hai?
        c.execute(
            "SELECT id FROM users WHERE username=? OR email=?",
            (username, final_email)
        )

        if c.fetchone():
            conn.close()
            flash("Username or Email already exists.", "error")
            return redirect(url_for("auth.register_verify"))

        # Account create karo
        c.execute(
            """
            INSERT INTO users
            (username, password, phone, email, dob, google_id)
            VALUES (?, ?, ?, ?, ?, ?)
            """,
            (
                username,
                hashed,
                phone,
                final_email,
                dob,
                google_id
            )
        )

        conn.commit()

        user_id = c.lastrowid

        conn.close()

        # Signup session clear
        session.pop("signup_username", None)
        session.pop("signup_password", None)
        session.pop("signup_dob", None)
        session.pop("google_email", None)
        session.pop("google_id", None)

        flash("Account created successfully!", "success")

        # Auto login
        session["user_id"] = user_id

        return redirect(url_for("posts.feed"))

    return render_template("register_verify.html")

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
    google_id = user_info["sub"]

    conn = sqlite3.connect("database.db")
    c = conn.cursor()

    # Agar pehle se account bana hua hai
    c.execute(
        "SELECT id FROM users WHERE google_id=? OR email=?",
        (google_id, email)
    )
    user = c.fetchone()

    if user:
        conn.close()
        session["user_id"] = user[0]
        return redirect(url_for("posts.feed"))

    # Google info save
    session["google_email"] = email
    session["google_id"] = google_id

    # Agar signup already complete ho chuka hai
    if (
        "signup_username" in session and
        "signup_password" in session and
        "signup_dob" in session
    ):

        username = session["signup_username"]
        password = session["signup_password"]
        dob = session["signup_dob"]

        hashed = generate_password_hash(password)

        # Username ya Email already exist?
        c.execute(
            "SELECT id FROM users WHERE username=? OR email=?",
            (username, email)
        )

        existing = c.fetchone()

        if existing:
            conn.close()
            flash("Username or Email already exists.", "error")
            return redirect(url_for("auth.register_verify"))

        # Account create
        c.execute(
            """
            INSERT INTO users
            (username, password, phone, email, dob, google_id)
            VALUES (?, ?, ?, ?, ?, ?)
            """,
            (
                username,
                hashed,
                "",
                email,
                dob,
                google_id
            )
        )

        conn.commit()

        user_id = c.lastrowid

        conn.close()

        # Signup session clear
        session.pop("signup_username", None)
        session.pop("signup_password", None)
        session.pop("signup_dob", None)
        session.pop("google_email", None)
        session.pop("google_id", None)

        # Auto login
        session["user_id"] = user_id

        return redirect(url_for("posts.feed"))

    conn.close()

    # Naya Google signup
    return redirect(url_for("auth.register_username"))
