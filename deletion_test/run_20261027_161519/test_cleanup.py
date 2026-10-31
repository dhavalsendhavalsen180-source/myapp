import sys
sys.path.insert(0, "/data/data/com.termux/files/home/inschit_app/myapp")
import os
import sqlite3
from routes.profile import cleanup_expired_posts_reels_follows

DB = os.path.abspath(
    "deletion_test/run_20261027_161519/database_test.db"
)

if not os.path.isfile(DB):
    raise SystemExit("ERROR: Test database nahi mili; live DB use nahi hogi.")

# Read-only pre-check: pending/expired accounts and their content counts.
con = sqlite3.connect(f"file:{DB}?mode=ro", uri=True)
try:
    print("TEST DATABASE:", DB)
    print("Integrity:", con.execute("PRAGMA integrity_check").fetchone()[0])

    users = con.execute("""
        SELECT id, username, deletion_expires_at
        FROM users
        WHERE deletion_requested_at IS NOT NULL
        ORDER BY id
    """).fetchall()

    print("Pending accounts:")
    for user in users:
        print(user)
finally:
    con.close()

print("\nDRY RUN ONLY — no deletion performed.")
print("Cleanup function imported successfully.")
print("Next: test the cleanup logic on a disposable copy, not the live database.")

print("\nRunning cleanup DRY RUN...")
result = cleanup_expired_posts_reels_follows(
    db_path=DB,
    dry_run=True,
)
print("DRY-RUN RESULT:", result)

con = sqlite3.connect(f"file:{DB}?mode=ro", uri=True)
try:
    print("Integrity after dry run:",
          con.execute("PRAGMA integrity_check").fetchone()[0])
finally:
    con.close()
