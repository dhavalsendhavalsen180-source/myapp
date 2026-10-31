import os
import sqlite3
from datetime import datetime

DB_NAME = "database.db"

# Sirf in app-media folders ko inspect karna hai.
MEDIA_DIRS = [
    "static/profile",
    "static/stories",
    "static/uploads",
]

def main():
    if not os.path.isfile(DB_NAME):
        print(f"ERROR: Database nahi mila: {DB_NAME}")
        return

    conn = sqlite3.connect(DB_NAME)
    conn.row_factory = sqlite3.Row

    try:
        now = datetime.now()

        users = conn.execute("""
            SELECT id, username, deletion_requested_at,
                   deletion_expires_at, suspended, banned
            FROM users
            WHERE deletion_requested_at IS NOT NULL
            ORDER BY deletion_expires_at
        """).fetchall()

        print("\n=== ACCOUNT DELETION DRY RUN ===")
        print("Mode: REPORT ONLY — koi data delete nahi hoga")
        print("Current time:", now.strftime("%Y-%m-%d %H:%M:%S"))
        print("Pending deletion requests:", len(users))

        eligible = []

        for user in users:
            print("\n--------------------------------")
            print("User ID:", user["id"])
            print("Username:", user["username"])
            print("Requested at:", user["deletion_requested_at"])
            print("Expires at:", user["deletion_expires_at"])
            print("Suspended:", user["suspended"])
            print("Banned:", user["banned"])

            expiry_text = user["deletion_expires_at"]

            try:
                if not expiry_text:
                    raise ValueError("Expiry date missing")
                expiry = datetime.strptime(
                    expiry_text, "%Y-%m-%d %H:%M:%S"
                )
            except (ValueError, TypeError):
                print("STATUS: REVIEW REQUIRED — expiry invalid/missing")
                continue

            if user["banned"] or user["suspended"]:
                print("STATUS: REVIEW REQUIRED — account restricted")
                continue

            if expiry <= now:
                print("STATUS: DEADLINE EXPIRED — eligible for review")
                eligible.append(user)
            else:
                print("STATUS: RECOVERY WINDOW STILL OPEN")

        print("\n=== MEDIA INVENTORY (COUNTS ONLY) ===")
        for folder in MEDIA_DIRS:
            count = 0
            size = 0

            if os.path.isdir(folder):
                for root, dirs, files in os.walk(folder):
                    for filename in files:
                        path = os.path.join(root, filename)
                        try:
                            if os.path.isfile(path):
                                count += 1
                                size += os.path.getsize(path)
                        except OSError:
                            pass

            print(f"{folder}: {count} files, {size} bytes")

        print("\n=== SUMMARY ===")
        print("Expired accounts requiring review:", len(eligible))
        print("Database changed: NO")
        print("Files deleted: NO")
        print("Backups changed: NO")
        print("\nThis script does not perform permanent deletion.")

    finally:
        conn.close()


if __name__ == "__main__":
    main()
