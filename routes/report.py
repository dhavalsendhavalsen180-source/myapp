from flask import Blueprint, request, session, redirect, flash, render_template
import sqlite3

report_bp = Blueprint("report", __name__, url_prefix="/report")

@report_bp.route("/", methods=["GET"])
def report_page():

    if "user_id" not in session:
        return redirect("/auth/login")

    return render_template(
        "report/index.html",
        target_type=request.args.get("target_type"),
        target_id=request.args.get("target_id"),
        owner_id=request.args.get("owner_id")
    )

@report_bp.route("/submit", methods=["POST"])
def submit_report():

    if "user_id" not in session:
        return redirect("/auth/login")

    reporter_id = session["user_id"]

    target_type = request.form.get("target_type")
    target_id = request.form.get("target_id")
    owner_id = request.form.get("owner_id")

    reason = request.form.get("reason")
    details = request.form.get("details", "")

    conn = sqlite3.connect("database.db")
    c = conn.cursor()

    # Same user ek hi content ko baar-baar report na kare
    c.execute("""
        SELECT id
        FROM reports
        WHERE reporter_id=?
        AND target_type=?
        AND target_id=?
    """, (
        reporter_id,
        target_type,
        target_id
    ))

    if c.fetchone():
        conn.close()
        flash("You already reported this.", "error")
        return redirect(request.referrer or "/")

    c.execute("""
        INSERT INTO reports
        (
            reporter_id,
            target_type,
            target_id,
            owner_id,
            reason,
            details
        )
        VALUES
        (?, ?, ?, ?, ?, ?)
    """, (
        reporter_id,
        target_type,
        target_id,
        owner_id,
        reason,
        details
    ))

    conn.commit()
    conn.close()

    return render_template("report/success.html")
