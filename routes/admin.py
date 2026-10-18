from flask import request, flash
from flask import Blueprint, render_template, session, redirect
import sqlite3
from socketio_init import socketio

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

    if report and report["owner_id"] == 1:
        conn.close()
        flash("Admin account cannot be suspended, banned, or changed through reports.")
        return redirect("/admin/reports")

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

        elif action == "unsuspend":

            c.execute("""
                UPDATE users
                SET suspended=0
                WHERE id=?
            """, (report["owner_id"],))

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
                "unsuspend",
                "User suspension removed"
            ))

            conn.commit()
            conn.close()

            flash("User unsuspended successfully.")
            return redirect("/admin/reports")

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

@admin_bp.route("/accounts", methods=["GET", "POST"])
def account_management():
    # Only Admin ID 1 can access this page
    if session.get("user_id") != 1:
        return redirect("/")

    conn = sqlite3.connect("database.db")
    conn.row_factory = sqlite3.Row
    c = conn.cursor()

    if request.method == "POST":
        action = (request.form.get("action") or "").strip().lower()
        user_id_raw = (request.form.get("user_id") or "").strip()

        try:
            target_user_id = int(user_id_raw)
        except (TypeError, ValueError):
            conn.close()
            flash("Invalid user ID.")
            return redirect("/admin/accounts")

        if target_user_id == 1:
            conn.close()
            flash("Admin account cannot be changed from this page.")
            return redirect("/admin/accounts")

        c.execute(
            "SELECT id, username, suspended, banned FROM users WHERE id=?",
            (target_user_id,)
        )
        target_user = c.fetchone()

        if not target_user:
            conn.close()
            flash("User not found.")
            return redirect("/admin/accounts")

        if action == "suspend":
            c.execute(
                "UPDATE users SET suspended=1 WHERE id=?",
                (target_user_id,)
            )
            note = "Account suspended from Account Management"

        elif action == "unsuspend":
            c.execute(
                "UPDATE users SET suspended=0 WHERE id=?",
                (target_user_id,)
            )
            note = "Account suspension removed from Account Management"

        elif action == "ban":
            c.execute(
                "UPDATE users SET banned=1 WHERE id=?",
                (target_user_id,)
            )
            note = "Account banned from Account Management"

        elif action == "unban":
            c.execute(
                "UPDATE users SET banned=0 WHERE id=?",
                (target_user_id,)
            )
            note = "Account ban removed from Account Management"

        else:
            conn.close()
            flash("Invalid action.")
            return redirect("/admin/accounts")

        c.execute("""
            INSERT INTO admin_logs
                (admin_id, report_id, owner_id, action, notes)
            VALUES (?, NULL, ?, ?, ?)
        """, (
            session["user_id"],
            target_user_id,
            action,
            note
        ))

        conn.commit()
        conn.close()

        # Notify the target user's active sessions in real time
        blocked = action in ("suspend", "ban")
        status = "banned" if action in ("ban", "unban") else "suspended"

        socketio.emit(
            "account_status_changed",
            {
                "blocked": blocked,
                "status": status,
                "message": (
                    "Your account has been banned."
                    if action == "ban"
                    else "Your account has been suspended."
                    if action == "suspend"
                    else "Your account status has been restored."
                ),
            },
            room=f"user_{target_user_id}",
        )

        flash("Account action completed successfully.")
        return redirect("/admin/accounts")

    search = (request.args.get("q") or "").strip()

    if search:
        if search.isdigit():
            c.execute("""
                SELECT
                    u.id,
                    u.username,
                    COALESCE(u.suspended, 0) AS suspended,
                    COALESCE(u.banned, 0) AS banned,
                    COALESCE(u.copyright_strikes, 0) AS copyright_strikes,
                    (
                        SELECT COUNT(*)
                        FROM reports r
                        WHERE r.owner_id = u.id
                    ) AS report_count
                FROM users u
                WHERE u.id = ? OR u.username LIKE ?
                ORDER BY u.id DESC
                LIMIT 100
            """, (int(search), "%" + search + "%"))
        else:
            c.execute("""
                SELECT
                    u.id,
                    u.username,
                    COALESCE(u.suspended, 0) AS suspended,
                    COALESCE(u.banned, 0) AS banned,
                    COALESCE(u.copyright_strikes, 0) AS copyright_strikes,
                    (
                        SELECT COUNT(*)
                        FROM reports r
                        WHERE r.owner_id = u.id
                    ) AS report_count
                FROM users u
                WHERE u.username LIKE ?
                ORDER BY u.id DESC
                LIMIT 100
            """, ("%" + search + "%",))
    else:
        c.execute("""
            SELECT
                u.id,
                u.username,
                COALESCE(u.suspended, 0) AS suspended,
                COALESCE(u.banned, 0) AS banned,
                COALESCE(u.copyright_strikes, 0) AS copyright_strikes,
                (
                    SELECT COUNT(*)
                    FROM reports r
                    WHERE r.owner_id = u.id
                ) AS report_count
            FROM users u
            ORDER BY u.id DESC
            LIMIT 100
        """)

    users = c.fetchall()

    c.execute("""
        SELECT
            l.id,
            l.admin_id,
            l.owner_id,
            l.action,
            l.notes,
            l.created_at,
            u.username AS owner_name
        FROM admin_logs l
        LEFT JOIN users u ON u.id = l.owner_id
        ORDER BY l.id DESC
        LIMIT 50
    """)
    logs = c.fetchall()

    conn.close()

    return render_template(
        "admin/accounts.html",
        users=users,
        logs=logs,
        search=search
    )
