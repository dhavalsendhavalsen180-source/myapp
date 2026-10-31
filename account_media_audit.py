import os
import sqlite3
from pathlib import Path

DB = Path("database.db").resolve()
ROOT = Path(".").resolve()

MEDIA_COLUMNS = {
    "users": ["photo"],
    "post_images": ["image_path"],
    "reels": ["video_path", "thumbnail"],
    "stories": ["media_path", "story_path"],
    "original_audio": ["audio_file"],
    "music": ["filename", "cover", "original_audio"],
}

def safe_media_path(value):
    if not value:
        return None

    value = str(value).strip()

    # Sirf app ke static media ko inspect karo.
    value = value.lstrip("/")
    if not value.startswith("static/"):
        return None

    path = (ROOT / value).resolve()

    try:
        path.relative_to(ROOT / "static")
    except ValueError:
        return None

    return path

def main():
    if not DB.is_file():
        print("ERROR: database.db nahi mila.")
        return

    conn = sqlite3.connect(f"file:{DB}?mode=ro", uri=True)
    conn.row_factory = sqlite3.Row

    try:
        users = conn.execute(
            """SELECT id, username, deletion_requested_at,
                      deletion_expires_at, suspended, banned
               FROM users ORDER BY id"""
        ).fetchall()

        print("=== READ-ONLY ACCOUNT MEDIA AUDIT ===")
        print("Accounts found:", len(users))
        print("Database writes: NO")
        print("Files deleted: NO")

        for user in users:
            uid = user["id"]
            print(f"\nUser ID: {uid} | Username: {user['username']}")
            print("Deletion requested:", user["deletion_requested_at"])
            print("Deletion expires:", user["deletion_expires_at"])
            print("Suspended/Banned:", user["suspended"], user["banned"])

            for table, columns in MEDIA_COLUMNS.items():
                if table == "users":
                    query = 'SELECT ' + ", ".join(
                        f'"{c}"' for c in columns
                    ) + ' FROM users WHERE id=?'
                    params = (uid,)
                elif table == "post_images":
                    query = """
                        SELECT pi.image_path
                        FROM post_images pi
                        JOIN posts p ON p.id=pi.post_id
                        WHERE p.user_id=?
                    """
                    params = (uid,)
                else:
                    if table == "reels":
                        owner = "user_id"
                    elif table == "stories":
                        owner = "user_id"
                    elif table == "original_audio":
                        owner = "user_id"
                    else:
                        owner = "uploaded_by"

                    query = (
                        "SELECT " + ", ".join(f'"{c}"' for c in columns)
                        + f' FROM "{table}" WHERE "{owner}"=?'
                    )
                    params = (uid,)

                try:
                    rows = conn.execute(query, params).fetchall()
                except sqlite3.Error as exc:
                    print(f"  {table}: REVIEW REQUIRED ({exc})")
                    continue

                for row in rows:
                    for column in columns:
                        path = safe_media_path(row[column])
                        if path:
                            status = "EXISTS" if path.is_file() else "MISSING"
                            print(f"  {table}.{column}: {status} — {path}")

        print("\nAudit complete. Nothing was changed.")

    finally:
        conn.close()

if __name__ == "__main__":
    main()
