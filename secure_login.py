# secure_login.py

import os, json, time, base64, hmac, hashlib, secrets, threading
from typing import Tuple, Dict, Any

# ---------- Storage ----------

DATA_DIR = os.path.abspath("./authdata")
USERS_PATH = os.path.join(DATA_DIR, "users.json")
SESSIONS_PATH = os.path.join(DATA_DIR, "sessions.json")
os.makedirs(DATA_DIR, exist_ok=True)

# ---------- Security config ----------

SERVER_SECRET = os.environ.get("AUTH_SERVER_SECRET") or base64.urlsafe_b64encode(os.urandom(32)).decode()
PEPPER = (os.environ.get("AUTH_PASSWORD_PEPPER") or "").encode()
SESSION_TTL = 60 * 60 * 24 * 7      # 7 days
CSRF_TTL = 60 * 60 * 12             # 12 hours
LOCK_THRESHOLD = 5                   # fail attempts in window
LOCK_WINDOW = 15 * 60                # 15 min window
LOCK_DURATION = 10 * 60              # lock for 10 min
RATE_LIMIT_IP = (10, 60)             # 10 attempts / 60 sec

# ---------- In-memory state ----------

_lock = threading.Lock()
USERS: Dict[str, Any] = {}
SESSIONS: Dict[str, Any] = {}
IP_BUCKETS: Dict[str, list] = {}  # ip -> [timestamps]

def _load():
    global USERS, SESSIONS
    if os.path.exists(USERS_PATH):
        with open(USERS_PATH, "r", encoding="utf-8") as f:
            USERS = json.load(f)
    else:
        USERS = {}
    if os.path.exists(SESSIONS_PATH):
        with open(SESSIONS_PATH, "r", encoding="utf-8") as f:
            SESSIONS = json.load(f)
    else:
        SESSIONS = {}

def _save():
    with _lock:
        with open(USERS_PATH, "w", encoding="utf-8") as f:
            json.dump(USERS, f)
        with open(SESSIONS_PATH, "w", encoding="utf-8") as f:
            json.dump(SESSIONS, f)

_load()

# ---------- Utils ----------

def _now() -> int:
    return int(time.time())

def _b64(b: bytes) -> str:
    return base64.urlsafe_b64encode(b).decode().rstrip("=")

def _b64d(s: str) -> bytes:
    pad = "=" * (-len(s) % 4)
    return base64.urlsafe_b64decode(s + pad)

def _hash_password(password: str, salt: bytes = None) -> Dict[str, str]:
    if salt is None:
        salt = os.urandom(16)
    key = hashlib.scrypt(
        password.encode("utf-8") + PEPPER,
        salt=salt,
        n=2**14,
        r=8,
        p=1,
        dklen=64
    )
    return {"algo": "scrypt", "salt": _b64(salt), "hash": _b64(key)}

def _verify_password(password: str, ph: Dict[str, str]) -> bool:
    try:
        salt = _b64d(ph["salt"])
        expected = _b64d(ph["hash"])
        calc = hashlib.scrypt(
            password.encode("utf-8") + PEPPER,
            salt=salt,
            n=2**14,
            r=8,
            p=1,
            dklen=64
        )
        return hmac.compare_digest(calc, expected)
    except Exception:
        return False

def _sign(value: str) -> str:
    mac = hmac.new(SERVER_SECRET.encode(), value.encode(), hashlib.sha256).digest()
    return f"{value}.{_b64(mac)}"

def _verify_signed(token: str) -> Tuple[bool, str]:
    try:
        value, sig = token.rsplit(".", 1)
        mac = hmac.new(SERVER_SECRET.encode(), value.encode(), hashlib.sha256).digest()
        return hmac.compare_digest(_b64(mac), sig), value
    except Exception:
        return False, ""

def _new_session(user: str) -> Dict[str, Any]:
    sid = _b64(os.urandom(32))
    csrf = _b64(os.urandom(24))
    now = _now()
    sess = {"user": user, "sid": sid, "csrf": csrf, "csrf_exp": now + CSRF_TTL, "exp": now + SESSION_TTL}
    SESSIONS[sid] = sess
    _save()
    token = _sign(f"{sid}|{sess['exp']}")
    return {"cookie": token, "csrf": csrf, "exp": sess["exp"]}

def _get_session_from_cookie(cookie_header: str) -> Dict[str, Any]:
    if not cookie_header:
        return None
    token = None
    for part in cookie_header.split(";"):
        part = part.strip()
        if part.startswith("inschat_session="):
            token = part.split("=", 1)[1].strip()
            break
    if not token:
        return None
    ok, raw = _verify_signed(token)
    if not ok:
        return None
    try:
        sid, exp = raw.split("|", 1)
        if _now() > int(exp):
            return None
        return SESSIONS.get(sid)
    except Exception:
        return None

def _refresh_csrf(sess: Dict[str, Any]) -> str:
    sess["csrf"] = _b64(os.urandom(24))
    sess["csrf_exp"] = _now() + CSRF_TTL
    _save()
    return sess["csrf"]

def _require_csrf(headers: Dict[str,str], sess: Dict[str,Any]) -> bool:
    token = headers.get("x-csrf-token") or headers.get("X-CSRF-Token")
    return bool(token) and token == sess.get("csrf") and _now() < sess.get("csrf_exp", 0)

def _rate_limit(ip: str) -> bool:
    if not ip:
        return False
    limit, window = RATE_LIMIT_IP
    bucket = IP_BUCKETS.setdefault(ip, [])
    now = _now()
    while bucket and bucket[0] < now - window:
        bucket.pop(0)
    if len(bucket) >= limit:
        return True
    bucket.append(now)
    return False

def _lock_status(u: Dict[str,Any]) -> Tuple[bool,int]:
    now = _now()
    locked_until = u.get("locked_until",0)
    if now < locked_until:
        return True, locked_until - now
    fails = [t for t in u.get("fails",[]) if now - t <= LOCK_WINDOW]
    u["fails"] = fails
    return False, 0

# ---------- Public API ----------

# secure_login.py ke end me (ya Public API section me) yeh add/replace karo

def whoami(cookie_header: str) -> Tuple[Dict[str, Any], int, Dict[str, str]]:
    """
    GET /auth/whoami — app.py is expecting (resp, code, headers)
    cookie_header: raw Cookie header string
    """
    sess = _get_session_from_cookie(cookie_header)
    if not sess:
        return {"ok": False, "user": None}, 401, {}
    return {"ok": True, "user": sess["user"]}, 200, {}
