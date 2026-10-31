import argparse
import json
import sqlite3
from pathlib import Path
from datetime import datetime, timezone

BASE = Path(__file__).resolve().parent
DB = BASE / "database_test.db"
MEDIA_ROOT = BASE / "media_sandbox" / "static"
EXPECTED_ID = 20
EXPECTED_USERNAME = "Testing1gmail"

# Child tables: delete records related to the user's own posts/reels.
POST_CHILDREN = {
    "post_images": ("post_id",),
    "likes": ("post_id",),
    "comments": ("post_id",),
    "post_saves": ("post_id",),
}

REEL_CHILDREN = {
    "reel_audio": ("reel_id",),
    "reel_likes": ("reel_id",),
    "reel_comments": ("reel_id",),
    "reel_comment_likes": ("reel_id",),
    "reel_views": ("reel_id",),
    "reel_shares": ("reel_id",),
    "reel_saves": ("reel_id",),
}

def columns(db, table):
    return {
        row[1]
        for row in db.execute(f'PRAGMA table_info("{table}")')
    }

def table_exists(db, table):
    return db.execute(
        "SELECT 1 FROM sqlite_master WHERE type='table' AND name=?",
        (table,),
    ).fetchone() is not None

def safe_media_path(raw):
    if not raw or not isinstance(raw, str):
        return None

    # Stored paths commonly look like /static/uploads/...
    rel = raw.replace("\\", "/").lstrip("/")
    if rel.startswith("static/"):
        rel = rel[len("static/"):]

    if not rel or ".." in Path(rel).parts:
        return None

    root = MEDIA_ROOT.resolve()
    candidate = (root / rel).resolve()

    try:
        candidate.relative_to(root)
    except ValueError:
        return None

    return candidate

def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("--execute", action="store_true",
                        help="Actually delete test-account data")
    args = parser.parse_args()

    if not DB.is_file() or not MEDIA_ROOT.is_dir():
        raise SystemExit("STOP: isolated test DB/media sandbox not found.")

    db = sqlite3.connect(DB)
    db.row_factory = sqlite3.Row
    db.execute("PRAGMA foreign_keys=ON")

    files_to_consider = set()

    try:
        integrity = db.execute("PRAGMA integrity_check").fetchone()[0]
        if integrity != "ok":
            raise RuntimeError(f"Database integrity failed: {integrity}")

        user = db.execute(
            """SELECT id, username, photo, deletion_requested_at,
                      deletion_expires_at
               FROM users WHERE id=?""",
            (EXPECTED_ID,),
        ).fetchone()

        if not user or user["username"] != EXPECTED_USERNAME:
            raise RuntimeError("Safety check failed: expected test account not found.")

        expiry = user["deletion_expires_at"]
        if not expiry:
            raise RuntimeError("No deletion expiry set; refusing cleanup.")

        # App stores timestamps as YYYY-MM-DD HH:MM:SS.
        expires = datetime.strptime(expiry, "%Y-%m-%d %H:%M:%S")
        now = datetime.now()
        if now < expires:
            raise RuntimeError("Account has not expired yet; refusing cleanup.")

        user_id = user["id"]
        posts = [r["id"] for r in db.execute(
            "SELECT id FROM posts WHERE user_id=?", (user_id,)
        )] if table_exists(db, "posts") else []

        reels = [r["id"] for r in db.execute(
            "SELECT id FROM reels WHERE user_id=?", (user_id,)
        )] if table_exists(db, "reels") else []

        stories = [dict(r) for r in db.execute(
            "SELECT * FROM stories WHERE user_id=?", (user_id,)
        )] if table_exists(db, "stories") else []

        post_rows = [dict(r) for r in db.execute(
            "SELECT * FROM posts WHERE user_id=?", (user_id,)
        )] if table_exists(db, "posts") else []

        reel_rows = [dict(r) for r in db.execute(
            "SELECT * FROM reels WHERE user_id=?", (user_id,)
        )] if table_exists(db, "reels") else []

        candidates = []
        if user["photo"]:
            candidates.append(user["photo"])

        for row in post_rows:
            if table_exists(db, "post_images"):
                for r in db.execute(
                    "SELECT image_path FROM post_images WHERE post_id=?",
                    (row["id"],),
                ):
                    candidates.append(r["image_path"])

        for row in reel_rows:
            for key in ("video_path", "thumbnail"):
                if row.get(key):
                    candidates.append(row[key])

        for row in stories:
            for key in ("media_path", "story_path"):
                if row.get(key):
                    candidates.append(row[key])

        media_files = []
        for raw in candidates:
            path = safe_media_path(raw)
            if path and path.is_file():
                media_files.append(path)

        plan = {
            "database": str(DB),
            "media_root": str(MEDIA_ROOT),
            "account": {"id": user_id, "username": user["username"]},
            "expired": True,
            "owned_posts": posts,
            "owned_reels": reels,
            "owned_stories": len(stories),
            "media_files_found": sorted({
                str(p.relative_to(MEDIA_ROOT.resolve()))
                for p in media_files
            }),
            "shared_chats": "PRESERVED",
            "backups": "NOT TOUCHED",
            "mode": "EXECUTE" if args.execute else "DRY RUN",
        }

        print(json.dumps(plan, indent=2))

        if not args.execute:
            print("\nDRY RUN ONLY: database and files were not changed.")
            return

        # Delete only records belonging to the selected account/content.
        # Keep chats themselves so the other participant's history remains.
        db.execute("BEGIN IMMEDIATE")

        if table_exists(db, "posts"):
            for post_id in posts:
                for table, fk_cols in POST_CHILDREN.items():
                    if table_exists(db, table):
                        cols = columns(db, table)
                        for fk in fk_cols:
                            if fk in cols:
                                db.execute(
                                    f'DELETE FROM "{table}" WHERE "{fk}"=?',
                                    (post_id,),
                                )

        if table_exists(db, "reels"):
            for reel_id in reels:
                for table, fk_cols in REEL_CHILDREN.items():
                    if table_exists(db, table):
                        cols = columns(db, table)
                        for fk in fk_cols:
                            if fk in cols:
                                db.execute(
                                    f'DELETE FROM "{table}" WHERE "{fk}"=?',
                                    (reel_id,),
                                )

        # Delete rows in user-owned content tables.
        for table in ("post_images", "posts", "reels", "stories",
                      "original_audio", "follow_requests", "follows",
                      "notifications", "music_saves", "original_audio_saves"):
            if not table_exists(db, table):
                continue
            cols = columns(db, table)

            if table == "post_images":
                # Already handled by post IDs above.
                continue
            if table == "follow_requests" and {"sender_id", "receiver_id"} <= cols:
                db.execute(
                    "DELETE FROM follow_requests WHERE sender_id=? OR receiver_id=?",
                    (user_id, user_id),
                )
            elif table == "follows" and {"follower_id", "following_id"} <= cols:
                db.execute(
                    "DELETE FROM follows WHERE follower_id=? OR following_id=?",
                    (user_id, user_id),
                )
            elif table == "notifications" and {"user_id", "actor_id"} <= cols:
                db.execute(
                    "DELETE FROM notifications WHERE user_id=? OR actor_id=?",
                    (user_id, user_id),
                )
            elif "user_id" in cols:
                db.execute(
                    f'DELETE FROM "{table}" WHERE user_id=?', (user_id,)
                )
            elif table == "music_saves" and "username" in cols:
                db.execute(
                    "DELETE FROM music_saves WHERE username=?",
                    (user["username"],),
                )
            elif table == "original_audio_saves" and "username" in cols:
                db.execute(
                    "DELETE FROM original_audio_saves WHERE username=?",
                    (user["username"],),
                )

        # Remove messages sent by this user, but preserve shared chat rows.
        if table_exists(db, "messages") and "sender_id" in columns(db, "messages"):
            db.execute("DELETE FROM messages WHERE sender_id=?", (user_id,))

        # Remove account references from other known tables when schema matches.
        for table, possible_cols in {
            "reports": ("reporter_id", "owner_id"),
            "copyright_reports": ("reporter_id", "owner_id", "user_id"),
            "admin_logs": ("owner_id",),
            "calls": ("caller_id", "receiver_id", "user_id"),
        }.items():
            if not table_exists(db, table):
                continue
            cols = columns(db, table)
            valid = [c for c in possible_cols if c in cols]
            if valid:
                where = " OR ".join(f'"{c}"=?' for c in valid)
                db.execute(
                    f'DELETE FROM "{table}" WHERE {where}',
                    tuple(user_id for _ in valid),
                )

        # Clean up user-created music only if no remaining rows reference it.
        if table_exists(db, "music") and "uploaded_by" in columns(db, "music"):
            music_cols = columns(db, "music")
            owned_music = [dict(r) for r in db.execute(
                "SELECT * FROM music WHERE uploaded_by=?", (user_id,)
            )]
            for item in owned_music:
                music_id = item.get("id")
                referenced = False
                for t, c in (("reels", "music_id"),
                             ("media_audio", "music_id"),
                             ("reel_audio", "music_id")):
                    if table_exists(db, t) and c in columns(db, t):
                        if db.execute(
                            f'SELECT 1 FROM "{t}" WHERE "{c}"=? LIMIT 1',
                            (music_id,),
                        ).fetchone():
                            referenced = True
                if not referenced:
                    db.execute("DELETE FROM music WHERE id=?", (music_id,))
                    for key in ("filename", "cover", "original_audio"):
                        if item.get(key):
                            candidates.append(item[key])

        db.execute("DELETE FROM users WHERE id=?", (user_id,))
        db.commit()

        # Delete only sandbox files, only after the DB transaction commits.
        # Do not remove files still referenced by any remaining media row.
        removed = []
        for raw in candidates:
            path = safe_media_path(raw)
            if not path or not path.is_file():
                continue
            rel = str(path.relative_to(MEDIA_ROOT.resolve()))
            referenced = False
            for table, col in (
                ("users", "photo"),
                ("post_images", "image_path"),
                ("reels", "video_path"),
                ("reels", "thumbnail"),
                ("stories", "media_path"),
                ("stories", "story_path"),
                ("original_audio", "audio_file"),
                ("music", "filename"),
                ("music", "cover"),
            ):
                if table_exists(db, table) and col in columns(db, table):
                    for r in db.execute(f'SELECT "{col}" FROM "{table}" WHERE "{col}" IS NOT NULL'):
                        other = safe_media_path(r[0])
                        if other and other.is_file() and str(other.resolve()) == str(path.resolve()):
                            referenced = True
                            break
                if referenced:
                    break
            if not referenced:
                path.unlink()
                removed.append(rel)

        print("\nEXECUTED on isolated test DB only.")
        print("Sandbox files removed:", removed)
        print("Shared chats preserved; backups untouched.")

    except Exception:
        if db.in_transaction:
            db.rollback()
        raise
    finally:
        db.close()

if __name__ == "__main__":
    main()
