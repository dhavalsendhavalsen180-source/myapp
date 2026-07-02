from flask import Blueprint, render_template, request, redirect, url_for, flash, session
import sqlite3
import random
import os
import requests

from werkzeug.security import generate_password_hash, check_password_hash
from datetime import datetime, timedelta
from authlib.integrations.flask_client import OAuth
from flask import current_app

BREVO_API_KEY = os.getenv("BREVO_API_KEY")

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
######################################################
def send_otp_email(to_email, otp):
    url = "https://api.brevo.com/v3/smtp/email"

    headers = {
        "accept": "application/json",
        "api-key": BREVO_API_KEY,
        "content-type": "application/json"
    }

    data = {
        "sender": {
            "name": "InsChat",
            "email": "inschatofficial.in@gmail.com"
        },
        "to": [
            {
                "email": to_email
            }
        ],
"subject": "InsChat Password Reset OTP",
"htmlContent": f"""
<!DOCTYPE html>
<html>
<head>
<meta charset="UTF-8">
<title>InsChat Password Reset</title>
</head>

<body style="margin:0;padding:0;background:#f3f4f6;font-family:Arial,Helvetica,sans-serif;">

<table width="100%" cellpadding="0" cellspacing="0" style="background:#f3f4f6;padding:40px 15px;">
<tr>
<td align="center">

<table width="100%" cellpadding="0" cellspacing="0"
style="max-width:520px;background:#ffffff;border-radius:18px;overflow:hidden;">

<tr>
<td style="background:#E1306C;padding:35px;text-align:center;">

<h1 style="margin:0;color:#fff;">
InsChat
</h1>

</td>
</tr>

<tr>
<td style="padding:35px;">

<h2>Reset your password</h2>

<p>Use the OTP below:</p>

<div style="background:#fafafa;border:2px dashed #E1306C;padding:20px;text-align:center;">

<h1 style="letter-spacing:8px;">
{otp}
</h1>

</div>

<p>This OTP is valid for <b>10 minutes</b>.</p>

<p>If you didn't request this, ignore this email.</p>

</td>
</tr>

</table>

</td>
</tr>
</table>

</body>
</html>
"""
    }

    r = requests.post(url, json=data, headers=headers)

    return r.status_code == 201


# ---------------- Login ----------------
@auth_bp.route("/login", methods=["GET", "POST"])
def login():
    if request.method == "POST":
        print("REGISTER VERIFY POST HIT")
        username = request.form.get("username", "").strip()
        password = request.form.get("password", "").strip()

        conn = sqlite3.connect("database.db")
        c = conn.cursor()

        # Username se user fetch karo
        c.execute(
            "SELECT id, password FROM users WHERE username=?",
            (username,)
        )
        row = c.fetchone()

        conn.close()

        if not row:
            flash("Invalid username or password!", "error")
            return render_template("login.html")

        user_id = row[0]
        stored_pass = row[1]

        # Password verify
        if check_password_hash(stored_pass, password):
            session["user_id"] = user_id
            session.permanent = True

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
# Ins Style Signup Flow
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

        try:
            print("REGISTER VERIFY POST HIT")

            import random

            print("STEP 1")

            phone = request.form.get("phone", "").strip()
            email = request.form.get("email", "").strip()

            print("STEP 2")
            print("Phone =", phone)
            print("Email =", email)

            username = session["signup_username"]
            print("STEP 3 =", username)

            final_email = email if email else session.get("google_email", "")
            google_id = session.get("google_id", None)

            # ✅ Sirf username unique hoga
            conn = sqlite3.connect("database.db")
            c = conn.cursor()

            c.execute(
                "SELECT id FROM users WHERE username=?",
                (username,)
            )

            if c.fetchone():
                conn.close()
                flash("Username already exists.", "error")
                return redirect(url_for("auth.register_verify"))

            conn.close()

            print("STEP 4 =", final_email)
            print("STEP 5")

            # Session me save
            session["signup_phone"] = phone
            session["signup_email"] = final_email
            session["google_id"] = google_id

            # OTP generate
            otp = str(random.randint(100000, 999999))
            session["signup_otp"] = otp

            print("==============================")
            print("InsChat OTP =", otp)
            print("==============================")

            flash("OTP generated.", "success")

            print("STEP 6 Redirecting to verify_phone")

            return redirect(url_for("auth.verify_phone"))

        except Exception as e:
            import traceback
            print("========== ERROR ==========")
            traceback.print_exc()
            print("===========================")
            flash(str(e), "error")
            return redirect(url_for("auth.register_verify"))

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
       "SELECT id FROM users WHERE google_id=?",
       (google_id,)
   )
    user = c.fetchone()

    if user:
        conn.close()
        session["user_id"] = user[0]
        session.permanent = True
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

         # Sirf username unique hoga
        c.execute(
            "SELECT id FROM users WHERE username=?",
            (username,)
        )

        existing = c.fetchone()

        if existing:
            conn.close()
            flash("Username already exists.", "error")
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
        session.permanent = True

        return redirect(url_for("posts.feed"))

    conn.close()

    # Naya Google signup
    return redirect(url_for("auth.register_username"))

##################### otp werifaye ###################
@auth_bp.route("/verify-phone", methods=["GET", "POST"])
def verify_phone():

    if "signup_otp" not in session:
        return redirect(url_for("auth.register_verify"))

    if request.method == "POST":

        code = request.form.get("code", "").strip()

        if code != session["signup_otp"]:
            flash("Invalid OTP", "error")
            return redirect(url_for("auth.verify_phone"))

        username = session["signup_username"]
        password = session["signup_password"]
        dob = session["signup_dob"]

        phone = session.get("signup_phone", "")
        email = session.get("signup_email", "")
        google_id = session.get("google_id")

        hashed = generate_password_hash(password)

        conn = sqlite3.connect("database.db")
        c = conn.cursor()

        c.execute("""
        INSERT INTO users
        (username, password, phone, email, dob, google_id)
        VALUES (?, ?, ?, ?, ?, ?)
        """, (
            username,
            hashed,
            phone,
            email,
            dob,
            google_id
        ))

        conn.commit()

        user_id = c.lastrowid

        conn.close()

        session.clear()

        session["user_id"] = user_id
        session.permanent = True

        return redirect(url_for("posts.feed"))

    return render_template("verify_phone.html")

#################### forget ########################
@auth_bp.route("/forgot-password", methods=["GET", "POST"])
def forgot_password():

    if request.method == "POST":

        login = request.form.get("login", "").strip()

        conn = sqlite3.connect("database.db")
        c = conn.cursor()

        c.execute("""
            SELECT id, username, phone, email
            FROM users
            WHERE username=? OR email=? OR phone=?
        """, (login, login, login))

        user = c.fetchone()

        conn.close()

        if not user:
            flash("No account found.", "error")
            return redirect(url_for("auth.forgot_password"))

        # user = (id, username, phone, email)

        if not user[3]:
            flash("This account doesn't have a recovery email.", "error")
            return redirect(url_for("auth.forgot_password"))

        otp = str(random.randint(100000, 999999))

        # Email par OTP bhejo

        if not send_otp_email(user[3], otp):
            flash("Failed to send OTP email.", "error")
            return redirect(url_for("auth.forgot_password"))
        session["reset_user_id"] = user[0]
        session["reset_otp"] = otp
        session["reset_otp_expiry"] = (
            datetime.now() + timedelta(minutes=10)
        ).strftime("%Y-%m-%d %H:%M:%S")

        session["reset_otp_attempts"] = 0

        # Email mask karke dikhana
        email = user[3]

        name, domain = email.split("@", 1)

        if len(name) > 2:
            masked = name[0] + "*" * (len(name) - 2) + name[-1]
        else:
            masked = name[0] + "*"

        masked_email = f"{masked}@{domain}"

        flash(f"OTP sent to {masked_email}", "success")

        return redirect(url_for("auth.verify_reset_otp"))

    return render_template("forgot_password.html")


##################### forget veryfy #################
@auth_bp.route("/forgot-password/verify", methods=["GET", "POST"])
def verify_reset_otp():

    if "reset_otp" not in session:
        return redirect(url_for("auth.forgot_password"))

    # OTP expiry check
    expiry = datetime.strptime(
        session["reset_otp_expiry"],
        "%Y-%m-%d %H:%M:%S"
    )

    if datetime.now() > expiry:
        session.pop("reset_user_id", None)
        session.pop("reset_otp", None)
        session.pop("reset_otp_expiry", None)

        flash("OTP has expired. Please request a new one.", "error")
        return redirect(url_for("auth.forgot_password"))

    if request.method == "POST":

        code = request.form.get("code", "").strip()

        attempts = session.get("reset_otp_attempts", 0)

        if attempts >= 5:
            flash("Too many incorrect attempts. Please request a new OTP.", "error")
            session.pop("reset_otp", None)
            session.pop("reset_otp_expiry", None)
            session.pop("reset_otp_attempts", None)
            return redirect(url_for("auth.forgot_password"))

        if code != session["reset_otp"]:
            session["reset_otp_attempts"] = attempts + 1

            remaining = 5 - session["reset_otp_attempts"]

            flash(f"Invalid OTP. {remaining} attempt(s) remaining.", "error")
            return redirect(url_for("auth.verify_reset_otp"))

    # Correct OTP
        session.pop("reset_otp_attempts", None)

        return redirect(url_for("auth.new_password"))


    return render_template("verify_reset_otp.html")

############################ resend ###################
@auth_bp.route("/forgot-password/resend", methods=["POST"])
def resend_reset_otp():

    if "reset_user_id" not in session:
        return redirect(url_for("auth.forgot_password"))

    conn = sqlite3.connect("database.db")
    c = conn.cursor()

    c.execute(
        "SELECT email FROM users WHERE id=?",
        (session["reset_user_id"],)
    )

    row = c.fetchone()

    conn.close()

    if not row or not row[0]:
        flash("Recovery email not found.", "error")
        return redirect(url_for("auth.forgot_password"))

    email = row[0]

    otp = str(random.randint(100000, 999999))

    if not send_otp_email(email, otp):
        flash("Failed to resend OTP.", "error")
        return redirect(url_for("auth.verify_reset_otp"))

    session["reset_otp"] = otp
    session["reset_otp_expiry"] = (
        datetime.now() + timedelta(minutes=10)
    ).strftime("%Y-%m-%d %H:%M:%S")
    session["reset_otp_attempts"] = 0

    flash("A new OTP has been sent.", "success")

    return redirect(url_for("auth.verify_reset_otp"))


######################## new password ###################
@auth_bp.route("/forgot-password/new-password", methods=["GET", "POST"])
def new_password():

    if "reset_user_id" not in session:
        return redirect(url_for("auth.forgot_password"))

    if request.method == "POST":

        password = request.form.get("password", "").strip()

        if len(password) < 8:
            flash("Password must be at least 8 characters.", "error")
            return redirect(url_for("auth.new_password"))

        hashed = generate_password_hash(password)

        conn = sqlite3.connect("database.db")
        c = conn.cursor()

        c.execute(
            "UPDATE users SET password=? WHERE id=?",
            (
                hashed,
                session["reset_user_id"]
            )
        )

        conn.commit()
        conn.close()

        session.pop("reset_user_id", None)
        session.pop("reset_otp", None)
        session.pop("reset_otp_expiry", None)

        flash("Password updated successfully.", "success")

        return redirect(url_for("auth.login"))

    return render_template("new_password.html")
