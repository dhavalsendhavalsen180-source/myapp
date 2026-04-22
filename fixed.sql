PRAGMA foreign_keys=OFF;
BEGIN TRANSACTION;
CREATE TABLE users (id INTEGER PRIMARY KEY AUTOINCREMENT, username TEXT UNIQUE, password TEXT, bio TEXT, photo TEXT);
INSERT INTO users VALUES(1,'Dhaval bhai','1234','Dhavalsen','/static/profile/user_1.jpg');
INSERT INTO users VALUES(2,'Vishal sen','4321',NULL,NULL);
INSERT INTO users VALUES(3,'Dhaval Kumar','1234',NULL,NULL);
INSERT INTO users VALUES(4,'Vishal bhai','1234',NULL,NULL);
CREATE TABLE posts (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    user_id INTEGER,
    caption TEXT,
    likes INTEGER DEFAULT 0,
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    FOREIGN KEY (user_id) REFERENCES users(id)
);
INSERT INTO posts VALUES(8,1,'Dharanidhar',0,'2025-11-25 03:02:40');
INSERT INTO posts VALUES(9,1,'',0,'2025-11-26 12:20:44');
CREATE TABLE post_images (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    post_id INTEGER,
    image_path TEXT,
    FOREIGN KEY (post_id) REFERENCES posts(id) ON DELETE CASCADE
);
INSERT INTO post_images VALUES(1,9,'5c4ff38ad8fd447eb362f4329618a59d_Screenshot_20251015_185726_One_UI_Home.png');
CREATE TABLE likes (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    post_id INTEGER,
    username TEXT, user_id INTEGER,
    FOREIGN KEY (post_id) REFERENCES posts(id) ON DELETE CASCADE
);
INSERT INTO likes VALUES(58,9,'Dhaval bhai',1);
CREATE TABLE comments (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    post_id INTEGER,
    user_id INTEGER,
    comment TEXT,
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    FOREIGN KEY (post_id) REFERENCES posts(id),
    FOREIGN KEY (user_id) REFERENCES users(id)
);
CREATE TABLE stories (
  id INTEGER PRIMARY KEY AUTOINCREMENT,
  user_id INTEGER,
  media_path TEXT,
  created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
  expires_at TIMESTAMP,
  FOREIGN KEY(user_id) REFERENCES users(id)
);
INSERT INTO stories VALUES(1,1,'','2025-11-26 12:35:28','2025-11-27 12:35:28');
INSERT INTO stories VALUES(2,1,'','2025-11-26 12:35:39','2025-11-27 12:35:39');
CREATE TABLE follows (
  id INTEGER PRIMARY KEY AUTOINCREMENT,
  follower_id INTEGER,
  following_id INTEGER,
  created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
  UNIQUE(follower_id, following_id)
);
INSERT INTO follows VALUES(1,2,1,'2025-11-21 05:03:05');
INSERT INTO follows VALUES(7,1,2,'2025-11-21 12:06:57');
INSERT INTO follows VALUES(8,3,1,'2025-11-21 12:44:58');
INSERT INTO follows VALUES(12,1,3,'2025-11-21 17:08:57');
INSERT INTO follows VALUES(14,4,1,'2025-11-21 17:11:59');
INSERT INTO follows VALUES(21,1,4,'2025-11-23 13:38:50');
CREATE TABLE notifications (
  id INTEGER PRIMARY KEY AUTOINCREMENT,
  user_id INTEGER,         -- who receives notification
  actor_id INTEGER,        -- who caused it (liker/commenter/follower)
  type TEXT,               -- 'like','comment','follow','story_view', etc
  meta TEXT,               -- json text: {"post_id":..,"comment_id":..}
  is_read INTEGER DEFAULT 0,
  created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
);
INSERT INTO notifications VALUES(1,1,2,'follow','{}',1,'2025-11-21 05:03:05');
INSERT INTO notifications VALUES(2,2,1,'follow','{}',0,'2025-11-21 07:08:14');
INSERT INTO notifications VALUES(3,2,1,'follow','{}',0,'2025-11-21 07:08:16');
INSERT INTO notifications VALUES(4,2,1,'follow','{}',0,'2025-11-21 07:08:18');
INSERT INTO notifications VALUES(5,2,1,'follow','{}',0,'2025-11-21 07:08:19');
INSERT INTO notifications VALUES(6,2,1,'follow','{}',0,'2025-11-21 07:08:20');
INSERT INTO notifications VALUES(7,2,1,'follow','{}',1,'2025-11-21 12:06:57');
INSERT INTO notifications VALUES(8,1,3,'follow','{}',0,'2025-11-21 12:44:58');
INSERT INTO notifications VALUES(9,3,1,'follow','{}',0,'2025-11-21 17:08:46');
INSERT INTO notifications VALUES(10,3,1,'follow','{}',0,'2025-11-21 17:08:48');
INSERT INTO notifications VALUES(11,3,1,'follow','{}',0,'2025-11-21 17:08:55');
INSERT INTO notifications VALUES(12,3,1,'follow','{}',0,'2025-11-21 17:08:57');
INSERT INTO notifications VALUES(13,1,4,'follow','{}',0,'2025-11-21 17:11:56');
INSERT INTO notifications VALUES(14,1,4,'follow','{}',0,'2025-11-21 17:11:59');
INSERT INTO notifications VALUES(15,4,1,'follow','{}',0,'2025-11-23 13:38:40');
INSERT INTO notifications VALUES(16,4,1,'follow','{}',0,'2025-11-23 13:38:43');
INSERT INTO notifications VALUES(17,4,1,'follow','{}',0,'2025-11-23 13:38:44');
INSERT INTO notifications VALUES(18,4,1,'follow','{}',0,'2025-11-23 13:38:45');
INSERT INTO notifications VALUES(19,4,1,'follow','{}',0,'2025-11-23 13:38:45');
INSERT INTO notifications VALUES(20,4,1,'follow','{}',0,'2025-11-23 13:38:46');
INSERT INTO notifications VALUES(21,4,1,'follow','{}',0,'2025-11-23 13:38:50');
INSERT INTO notifications VALUES(22,4,2,'follow','{}',0,'2025-11-23 13:55:29');
INSERT INTO notifications VALUES(23,4,2,'follow','{}',0,'2025-11-23 13:55:31');
INSERT INTO notifications VALUES(24,4,2,'follow','{}',0,'2025-11-23 13:55:31');
INSERT INTO notifications VALUES(25,4,2,'follow','{}',0,'2025-11-23 13:55:32');
CREATE TABLE reels (  
    id INTEGER PRIMARY KEY AUTOINCREMENT,  
    user_id INTEGER,  
    caption TEXT,  
    video_path TEXT  
);
INSERT INTO reels VALUES(1,0,'','eeb0b2e0-cf9a-444e-b246-9de40d02379f.mp4');
INSERT INTO reels VALUES(2,0,'','2964a392-2a6d-4826-a736-cc947b75a9e0.mp4');
INSERT INTO reels VALUES(3,1,'','489b940883d045b699c87a2b1f931e73.mp4');
INSERT INTO reels VALUES(4,1,'','b7ac6539262f484a86ac49713ef7211f.mp4');
INSERT INTO reels VALUES(5,1,'','af028c936fca4b4aa15a8bc21a1c9829.mp4');
CREATE TABLE reel_likes (  
    id INTEGER PRIMARY KEY AUTOINCREMENT,  
    reel_id INTEGER,  
    user_id INTEGER  
);
CREATE TABLE reel_comments (  
    id INTEGER PRIMARY KEY AUTOINCREMENT,  
    reel_id INTEGER,  
    user_id INTEGER,  
    comment TEXT  
);
CREATE TABLE reel_saves (  
    id INTEGER PRIMARY KEY AUTOINCREMENT,  
    reel_id INTEGER,  
    user_id INTEGER  
);
PRAGMA writable_schema=ON;
CREATE TABLE IF NOT EXISTS sqlite_sequence(name,seq);
DELETE FROM sqlite_sequence;
INSERT INTO sqlite_sequence VALUES('users',4);
INSERT INTO sqlite_sequence VALUES('posts',9);
INSERT INTO sqlite_sequence VALUES('likes',58);
INSERT INTO sqlite_sequence VALUES('comments',3);
INSERT INTO sqlite_sequence VALUES('follows',25);
INSERT INTO sqlite_sequence VALUES('notifications',25);
INSERT INTO sqlite_sequence VALUES('reels',5);
INSERT INTO sqlite_sequence VALUES('post_images',1);
INSERT INTO sqlite_sequence VALUES('stories',2);
PRAGMA writable_schema=OFF;
COMMIT;
