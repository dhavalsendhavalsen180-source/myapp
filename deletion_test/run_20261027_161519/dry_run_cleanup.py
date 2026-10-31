import sqlite3
from pathlib import Path
from datetime import datetime

ROOT = Path(__file__).resolve().parent
DB_PATH = ROOT / "database_test.db"
STATIC = (ROOT / "media_sandbox" / "static").resolve()
UID = 20
USERNAME = "Testing1gmail"

if not DB_PATH.is_file() or not STATIC.is_dir():
    raise SystemExit("STOP: Test DB ya sandbox missing hai.")

db = sqlite3.connect(f"file:{DB_PATH}?mode=ro", uri=True)
db.row_factory = sqlite3.Row

def count(table, where, params=(UID,)):
    return db.execute(
        f'SELECT COUNT(*) FROM "{table}" WHERE {where}', params
    ).fetchone()[0]

def resolve_media(raw, kind):
    if not raw:
        return None

    name = str(raw).replace("\\", "/").split("/")[-1]

    folders = {
        "profile": ["profile"],
        "post": ["uploads/posts"],
        "reel": ["uploads/reels"],
        "thumbnail": ["uploads/reels/thumbs"],
        "story": ["uploads", "uploads/stories"],
        "audio": ["uploads/original_audio"],
    }.get(kind, [])

    for folder in folders:
        candidate = (STATIC / folder / name).resolve()
        try:
            candidate.relative_to(STATIC)
        except ValueError:
            continue
        if candidate.is_file():
            return candidate

    return None

try:
    print("=== CORRECTED DRY RUN — REPORT ONLY ===")
    print("Integrity:", db.execute("PRAGMA integrity_check").fetchone()[0])

    user = db.execute("""
        SELECT id, username, photo, deletion_requested_at,
               deletion_expires_at
        FROM users WHERE id=? AND username=?
    """, (UID, USERNAME)).fetchone()

    if not user:
        raise SystemExit("STOP: Test account missing hai.")

    print("\nAccount:", dict(user))

    if not user["deletion_requested_at"] or not user["deletion_expires_at"]:
        raise SystemExit("STOP: Deletion timestamps missing hain.")

    expiry = datetime.strptime(
        user["deletion_expires_at"], "%Y-%m-%d %H:%M:%S"
    )
    print("Expiry:", expiry)
    print("Expired:", expiry <= datetime.now())

    tables = {
        r["name"] for r in db.execute("""
            SELECT name FROM sqlite_master WHERE type='table'
        """)
    }

    print("\n=== RELATED RECORD COUNTS ===")
    checks = [
        ("posts", "user_id=?"),
        ("reels", "user_id=?"),
        ("stories", "user_id=?"),
        ("original_audio", "user_id=?"),
        ("follows: as follower", "follows", "follower_id=?"),
        ("follows: as following", "follows", "following_id=?"),
        ("follow_requests: sender", "follow_requests", "sender_id=?"),
        ("follow_requests: receiver", "follow_requests", "receiver_id=?"),
        ("notifications: recipient", "notifications", "user_id=?"),
        ("notifications: actor", "notifications", "actor_id=?"),
        ("comments", "comments", "user_id=?"),
        ("reel_comments", "reel_comments", "user_id=?"),
        ("reel_likes", "reel_likes", "user_id=?"),
        ("reel_views", "reel_views", "user_id=?"),
        ("reel_shares: sender", "reel_shares", "sender_id=?"),
        ("reel_shares: receiver", "reel_shares", "receiver_id=?"),
        ("reel_saves", "reel_saves", "user_id=?"),
        ("post_saves", "post_saves", "user_id=?"),
        ("music_saves", "music_saves", "user_id=?"),
        ("original_audio_saves", "original_audio_saves", "user_id=?"),
    ]

    for item in checks:
        if len(item) == 2:
            label, where = item
            table = label
        else:
            label, table, where = item

        if table not in tables:
            print(f"{label}: table absent")
            continue

        cols = {
            r["name"] for r in db.execute(f'PRAGMA table_info("{table}")')
        }
        col = where.split("=")[0].strip()
        if col not in cols:
            print(f"{label}: column absent")
            continue

        print(f"{label}: {count(table, where)}")

    print("\n=== MEDIA PATH CHECK ===")
    media = []

    if user["photo"]:
        media.append(("Profile photo", user["photo"], "profile"))

    for r in db.execute("""
        SELECT p.id, pi.image_path
        FROM posts p JOIN post_images pi ON pi.post_id=p.id
        WHERE p.user_id=?
    """, (UID,)):
        media.append((f"Post {r['id']}", r["image_path"], "post"))

    for r in db.execute("""
        SELECT id, video_path, thumbnail FROM reels WHERE user_id=?
    """, (UID,)):
        media.append((f"Reel {r['id']} media", r["video_path"], "reel"))
        media.append((f"Reel {r['id']} thumbnail", r["thumbnail"], "thumbnail"))

    for r in db.execute("""
        SELECT id, media_path, story_path FROM stories WHERE user_id=?
    """, (UID,)):
        media.append((f"Story {r['id']} media", r["media_path"], "story"))
        media.append((f"Story {r['id']} story_path", r["story_path"], "story"))

    for r in db.execute("""
        SELECT id, audio_file FROM original_audio WHERE user_id=?
    """, (UID,)):
        media.append((f"Original audio {r['id']}", r["audio_file"], "audio"))

    for label, raw, kind in media:
        path = resolve_media(raw, kind)
        print(f"{label}: {raw!r} | sandbox file found={path is not None}")
        if path:
            print("  Resolved:", path.relative_to(STATIC))

    print("\nDatabase changed: NO")
    print("Files deleted: NO")
    print("Backups changed: NO")

finally:
    db.close()
