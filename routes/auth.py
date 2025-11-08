from flask import Blueprint, render_template, request, redirect, url_for, flash, session
import sqlite3

auth_bp = Blueprint("auth", __name__, url_prefix="/auth")

# ---------------- Register ----------------
@auth_bp.route("/register", methods=["GET", "POST"])
def register():
    if request.method == "POST":
        username = request.form["username"]
        password = request.form["password"]

        conn = sqlite3.connect("database.db")
        c = conn.cursor()

        # check duplicate user
        c.execute("SELECT * FROM users WHERE username=?", (username,))
        if c.fetchone():
            conn.close()
            flash("Username already exists!", "error")
            return redirect(url_for("auth.register"))

        c.execute("INSERT INTO users (username, password) VALUES (?, ?)", (username, password))
        conn.commit()
        conn.close()

        flash("Registration successful! Please login.", "success")
        return redirect(url_for("auth.login"))

    return render_template("register.html")


# ---------------- Login ----------------

@auth_bp.route("/login", methods=["GET", "POST"])
def login():
    if request.method == "POST":
        username = request.form["username"]
        password = request.form["password"]

        conn = sqlite3.connect("database.db")
        c = conn.cursor()
        c.execute("SELECT id, username FROM users WHERE username=? AND password=?", (username, password))
        user = c.fetchone()
        conn.close()

        if user:
            session["user_id"] = user[0]    # ✅ id save
            session["user"] = user[1]       # ✅ username save
            flash("Login successful!", "success")
            return redirect(url_for("posts.feed"))  # ✅ feed redirect
        else:
            flash("Invalid username or password", "error")
            return render_template("login.html")

    return render_template("login.html")


# ---------------- Logout ----------------
@auth_bp.route("/logout")
def logout():
    session.clear()   # ✅ pura session clear
    flash("Logged out successfully!", "info")
    return redirect(url_for("auth.login"))
