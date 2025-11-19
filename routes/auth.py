from flask import Blueprint, render_template, request, redirect, url_for, flash, session
import sqlite3

auth_bp = Blueprint("auth", __name__, url_prefix="/auth")

# ---------------- Register ----------------
@auth_bp.route("/register", methods=["GET", "POST"])
def register():
    if request.method == "POST":
        username = request.form.get("username", "").strip()
        password = request.form.get("password", "").strip()

        if not username or not password:
            flash("Username and password cannot be empty!", "error")
            return redirect(url_for("auth.register"))

        conn = sqlite3.connect("database.db")
        c = conn.cursor()

        # duplicate check
        c.execute("SELECT id FROM users WHERE username=?", (username,))
        if c.fetchone():
            conn.close()
            flash("Username already exists!", "error")
            return redirect(url_for("auth.register"))

        # insert new user
        c.execute("INSERT INTO users (username, password) VALUES (?, ?)", (username, password))
        conn.commit()
        conn.close()

        flash("Registration successful!", "success")
        return redirect(url_for("auth.login"))

    return render_template("register.html")


# ---------------- Login ----------------
@auth_bp.route("/login", methods=["GET", "POST"])
def login():
    if request.method == "POST":
        username = request.form.get("username", "").strip()
        password = request.form.get("password", "").strip()

        print(f"🟢 Login attempt: {username} / {password}")

        conn = sqlite3.connect("database.db")
        c = conn.cursor()
        c.execute("SELECT id, username FROM users WHERE username=? AND password=?", (username, password))
        user = c.fetchone()
        conn.close()

        print("🟢 Query result:", user)

        if user:
            session["user_id"] = user[0]
            session["user"] = user[1]
            flash("Login successful!", "success")
            return redirect(url_for("posts.feed"))
        else:
            flash("Invalid username or password!", "error")
            return render_template("login.html")

    return render_template("login.html")
