import sqlite3, bcrypt, jwt, datetime

SECRET = "MY_SUPER_SECRET_KEY"

# =========================
# USERS DB
# =========================
def init_users_db():
    conn = sqlite3.connect("users.db")
    cur = conn.cursor()
    cur.execute("""
        CREATE TABLE IF NOT EXISTS users (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            username TEXT UNIQUE,
            password BLOB
        )
    """)
    conn.commit()
    conn.close()

def register(username, password):
    try:
        hashed = bcrypt.hashpw(password.encode(), bcrypt.gensalt())
        conn = sqlite3.connect("users.db")
        cur = conn.cursor()
        cur.execute("INSERT INTO users(username,password) VALUES(?,?)", (username, hashed))
        conn.commit()
        conn.close()
        return {"msg": "User registered"}, 201
    except Exception as e:
        return {"error": "Username already exists"}, 400

def login(username, password):
    conn = sqlite3.connect("users.db")
    cur = conn.cursor()
    cur.execute("SELECT password FROM users WHERE username=?", (username,))
    row = cur.fetchone()
    conn.close()
    if not row:
        return {"error": "Invalid credentials"}, 401
    
    stored_password = row[0]
    # sqlite may return str, convert to bytes if needed
    if isinstance(stored_password, str):
        stored_password = stored_password.encode()

    if not bcrypt.checkpw(password.encode(), stored_password):
        return {"error": "Invalid credentials"}, 401

    payload = {"user": username, "exp": datetime.datetime.utcnow() + datetime.timedelta(hours=1)}
    token = jwt.encode(payload, SECRET, algorithm="HS256")
    return {"token": token}, 200

def verify(token):
    if not token:
        return None, 401
    try:
        data = jwt.decode(token, SECRET, algorithms=["HS256"])
        return data["user"], 200
    except jwt.ExpiredSignatureError:
        return None, 401
    except jwt.InvalidTokenError:
        return None, 401


# =========================
# POSTS DB
# =========================
def init_posts_db():
    conn = sqlite3.connect("inschat.db")
    c = conn.cursor()
    c.execute('''
        CREATE TABLE IF NOT EXISTS posts (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            user TEXT,
            caption TEXT,
            image_path TEXT,
            created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
        )
    ''')
    conn.commit()
    conn.close()






def init_posts_extras():
    conn = sqlite3.connect("inschat.db")
    c = conn.cursor()
    # Likes table
    c.execute("""
        CREATE TABLE IF NOT EXISTS likes (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            post_id INTEGER,
            user TEXT
        )
    """)
    # Comments table
    c.execute("""
        CREATE TABLE IF NOT EXISTS comments (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            post_id INTEGER,
            user TEXT,
            text TEXT
        )
    """)
    conn.commit()
    conn.close()
