from flask import request, flash
from flask import Blueprint, render_template, session, redirect
import sqlite3

admin_bp = Blueprint("admin", __name__, url_prefix="/admin")


@admin_bp.route("/reports")
def reports():

    # ⚠️ Apna admin user id yahan change kar sakte ho
    if session.get("user_id") != 1:
        return redirect("/")

    conn = sqlite3.connect("database.db")
    conn.row_factory = sqlite3.Row
    c = conn.cursor()

    c.execute("""
        SELECT
            reports.*,
            users.username AS reporter_name
        FROM reports
        LEFT JOIN users
            ON users.id = reports.reporter_id
        WHERE status='pending'
        ORDER BY id DESC
    """)

    reports = c.fetchall()

    conn.close()

    return render_template(
        "admin/reports.html",
        reports=reports
    )

@admin_bp.route("/report/<int:report_id>", methods=["GET", "POST"])
def review_report(report_id):

    if session.get("user_id") != 1:
        return redirect("/")

    conn = sqlite3.connect("database.db")
    conn.row_factory = sqlite3.Row
    c = conn.cursor()

    c.execute("""
        SELECT
            reports.*,
            reporter.username AS reporter_name,
            owner.username AS owner_name

        FROM reports

        LEFT JOIN users AS reporter
            ON reporter.id = reports.reporter_id

        LEFT JOIN users AS owner
            ON owner.id = reports.owner_id

        WHERE reports.id=?

    """, (report_id,))

    report = c.fetchone()

    if not report:
        conn.close()
        flash("Report not found.")
        return redirect("/admin/reports")

    c.execute("""
        SELECT COUNT(*)
        FROM reports
        WHERE
            target_type=?
            AND target_id=?
    """, (
        report["target_type"],
        report["target_id"]
    ))

    total_reports = c.fetchone()[0]

    c.execute("""
        SELECT
            COUNT(*) AS total_posts
        FROM posts
        WHERE user_id=?
    """, (report["owner_id"],))

    total_posts = c.fetchone()["total_posts"]


    c.execute("""
        SELECT
            copyright_strikes,
            suspended,
            banned
        FROM users
        WHERE id=?
    """, (report["owner_id"],))

    owner_info = c.fetchone()

    c.execute("""
        SELECT
            id,
            reason,
            status,
            created_at
        FROM reports
        WHERE owner_id=?
        ORDER BY created_at DESC
        LIMIT 10
    """, (report["owner_id"],))

    report_history = c.fetchall()

    if request.method == "POST":

        action = request.form.get("action")

        if action == "reject":

            c.execute("""
                UPDATE reports
                SET status='rejected'
                WHERE id=?
            """, (report_id,))

        elif action == "approve":

            # ---------- POST ----------
            if report["target_type"] == "post":

                c.execute("DELETE FROM posts WHERE id=?", (report["target_id"],))
                c.execute("DELETE FROM post_images WHERE post_id=?", (report["target_id"],))
                c.execute("DELETE FROM likes WHERE post_id=?", (report["target_id"],))
                c.execute("DELETE FROM comments WHERE post_id=?", (report["target_id"],))

            # ---------- MUSIC ----------
            elif report["target_type"] == "music":

                c.execute("""
                    UPDATE music
                    SET blocked=1
                    WHERE id=?
                """, (report["target_id"],))

                c.execute("""
                    UPDATE users
                    SET copyright_strikes = copyright_strikes + 1
                    WHERE id=?
                """, (report["owner_id"],))

                c.execute("""
                    SELECT copyright_strikes
                    FROM users
                    WHERE id=?
                """, (report["owner_id"],))

                strikes = c.fetchone()[0]

                if strikes >= 3:

                    c.execute("""
                        UPDATE users
                        SET suspended=1
                        WHERE id=?
                    """, (report["owner_id"],))

            c.execute("""
                UPDATE reports
                SET status='approved'
                WHERE id=?
            """, (report_id,))

        elif action == "suspend":

            c.execute("""
                UPDATE users
                SET suspended=1
                WHERE id=?
            """, (report["owner_id"],))

            if report["target_type"] == "music":
                c.execute("""
                    UPDATE music
                    SET blocked=1
                    WHERE id=?
                """, (report["target_id"],))

            c.execute("""
                UPDATE reports
                SET status='approved'
                WHERE id=?
            """, (report_id,))

        elif action == "ban":

            c.execute("""
                UPDATE users
                SET banned=1
                WHERE id=?
            """, (report["owner_id"],))

            if report["target_type"] == "music":
                c.execute("""
                    UPDATE music
                    SET blocked=1
                    WHERE id=?
                """, (report["target_id"],))

            c.execute("""
                UPDATE reports
                SET status='approved'
                WHERE id=?
            """, (report_id,))

        c.execute("""
            INSERT INTO admin_logs
            (
                admin_id,
                report_id,
                owner_id,
                action,
                notes
            )
            VALUES (?, ?, ?, ?, ?)
        """, (
            session["user_id"],
            report_id,
            report["owner_id"],
            action,
            report["reason"]
        ))

        conn.commit()
        conn.close()

        flash("Action completed.")
        return redirect("/admin/reports")

    post = None
    images = []

    if report["target_type"] == "post":

        c.execute("""
            SELECT
                posts.*,
                users.username,
                users.photo,

                (
                    SELECT image_path
                    FROM post_images
                    WHERE post_id = posts.id
                    LIMIT 1
                ) AS image

            FROM posts

            JOIN users
                ON users.id = posts.user_id

            WHERE posts.id=?

        """, (report["target_id"],))

        post = c.fetchone()

        if post:

            c.execute("""
                SELECT image_path
                FROM post_images
                WHERE post_id=?
                ORDER BY id
            """, (post["id"],))

            images = c.fetchall()

    elif report["target_type"] == "music":

        c.execute("""
            SELECT *
            FROM music
            WHERE id=?
        """, (report["target_id"],))

        post = c.fetchone()

    conn.close()

    return render_template(
            "admin/review_report.html",
            report=report,
            post=post,
            images=images,
            total_reports=total_reports,
            total_posts=total_posts,
            owner_info=owner_info,
            report_history=report_history
        )
