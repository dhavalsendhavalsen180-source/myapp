import sqlite3
from datetime import datetime
import os

DB = "database.db"

# User-owned rows and rows linked through owned posts, reels,
# stories, chats, messages, and original audio.
def main():
    if not os.path.isfile(DB):
        print("ERROR: database.db nahi mila.")
        return

    con = sqlite3.connect(f"file:{DB}?mode=ro", uri=True)
    con.row_factory = sqlite3.Row

    checks = [
        ("Posts", "SELECT COUNT(*) FROM posts WHERE user_id=?"),
        ("Post images", """
            SELECT COUNT(*) FROM post_images
            WHERE post_id IN (SELECT id FROM posts WHERE user_id=?)
        """),
        ("Reels", "SELECT COUNT(*) FROM reels WHERE user_id=?"),
        ("Stories", "SELECT COUNT(*) FROM stories WHERE user_id=?"),
        ("Comments", "SELECT COUNT(*) FROM comments WHERE user_id=?"),
        ("Reel comments", "SELECT COUNT(*) FROM reel_comments WHERE user_id=?"),
        ("Post likes", "SELECT COUNT(*) FROM likes WHERE user_id=?"),
        ("Reel likes", "SELECT COUNT(*) FROM reel_likes WHERE user_id=?"),
        ("Follows as follower", "SELECT COUNT(*) FROM follows WHERE follower_id=?"),
        ("Follows as following", "SELECT COUNT(*) FROM follows WHERE following_id=?"),
        ("Follow requests sent", "SELECT COUNT(*) FROM follow_requests WHERE sender_id=?"),
        ("Follow requests received", "SELECT COUNT(*) FROM follow_requests WHERE receiver_id=?"),
        ("Notifications received", "SELECT COUNT(*) FROM notifications WHERE user_id=?"),
        ("Notifications generated", "SELECT COUNT(*) FROM notifications WHERE actor_id=?"),
        ("Chats", "SELECT COUNT(*) FROM chats WHERE user1=? OR user2=?"),
        ("Messages sent", "SELECT COUNT(*) FROM messages WHERE sender_id=?"),
        ("Message receipts", "SELECT COUNT(*) FROM message_receipts WHERE user_id=?"),
        ("Message screenshots", "SELECT COUNT(*) FROM message_screenshots WHERE user_id=?"),
        ("Calls initiated", "SELECT COUNT(*) FROM calls WHERE caller_id=?"),
        ("Calls received", "SELECT COUNT(*) FROM calls WHERE receiver_id=?"),
        ("Music uploaded", "SELECT COUNT(*) FROM music WHERE uploaded_by=?"),
        ("Original audio", "SELECT COUNT(*) FROM original_audio WHERE user_id=?"),
        ("Reports submitted", "SELECT COUNT(*) FROM reports WHERE reporter_id=?"),
        ("Reports against account", "SELECT COUNT(*) FROM reports WHERE owner_id=?"),
    ]

    try:
        now = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
        users = con.execute("""
            SELECT id, username, deletion_requested_at,
                   deletion_expires_at, suspended, banned
            FROM users
            WHERE deletion_requested_at IS NOT NULL
            ORDER BY deletion_expires_at
        """).fetchall()

        print("=== READ-ONLY ACCOUNT DELETION AUDIT ===")
        print("Time:", now)
        print("Pending accounts:", len(users))
        print("Database writes: NONE")
        print("File deletion: NONE")
        print("Backup changes: NONE")

        for u in users:
            uid = u["id"]
            print("\n" + "=" * 42)
            print("User ID:", uid)
            print("Username:", u["username"])
            print("Requested:", u["deletion_requested_at"])
            print("Expiry:", u["deletion_expires_at"])
            print("Suspended:", u["suspended"])
            print("Banned:", u["banned"])

            try:
                expiry = datetime.strptime(
                    u["deletion_expires_at"], "%Y-%m-%d %H:%M:%S"
                )
                status = "EXPIRED — NEEDS REVIEW" if expiry <= datetime.now() \
                    else "RECOVERY WINDOW OPEN"
            except (ValueError, TypeError):
                status = "INVALID/MISSING EXPIRY — NEEDS REVIEW"

            if u["suspended"] or u["banned"]:
                status += " (ACCOUNT RESTRICTED; DO NOT AUTO-DELETE)"
            print("Status:", status)

            for label, sql in checks:
                params = (uid, uid) if "OR user1=?" in sql else (uid,)
                count = con.execute(sql, params).fetchone()[0]
                print(f"{label}: {count}")

        print("\nAudit complete. No data was changed.")
    finally:
        con.close()

if __name__ == "__main__":
    main()
