"""drift — a small, quiet social feed.

Flask + SQLite backend serving a paginated feed of posts that can hold text,
images, videos, or any combination of the three.
"""

from __future__ import annotations

import os
import re
import sqlite3
import uuid
from datetime import datetime, timezone

from flask import Flask, g, jsonify, request, send_from_directory
from werkzeug.exceptions import RequestEntityTooLarge

BASE_DIR = os.path.dirname(os.path.abspath(__file__))

# The database and uploaded media live under STORAGE_DIR so a container can
# mount a persistent volume there (Fly.io mounts one at /data). Unset, it falls
# back to backend/ and local development behaves exactly as before.
STORAGE_DIR = os.path.abspath(os.environ.get("STORAGE_DIR") or BASE_DIR)
DATA_DIR = os.path.join(STORAGE_DIR, "data")
UPLOAD_DIR = os.path.join(STORAGE_DIR, "uploads")
DB_PATH = os.path.join(DATA_DIR, "app.db")
DIST_DIR = os.path.abspath(os.path.join(BASE_DIR, "..", "frontend", "dist"))

MAX_TEXT = 2000
MAX_FILES = 6
MAX_FILE_BYTES = 25 * 1024 * 1024

# Only these media types are stored, and the stored extension always comes
# from this table (never from the client's filename) so uploads cannot be
# served back as HTML or scripts.
IMAGE_TYPES = {
    "image/jpeg": ".jpg",
    "image/png": ".png",
    "image/gif": ".gif",
    "image/webp": ".webp",
}
VIDEO_TYPES = {
    "video/mp4": ".mp4",
    "video/webm": ".webm",
    "video/quicktime": ".mov",
}
MIME_BY_EXT = {ext: mime for mime, ext in {**IMAGE_TYPES, **VIDEO_TYPES}.items()}

SCHEMA = """
CREATE TABLE IF NOT EXISTS posts (
    id          INTEGER PRIMARY KEY AUTOINCREMENT,
    author_name TEXT    NOT NULL,
    author_handle TEXT  NOT NULL,
    text        TEXT    NOT NULL DEFAULT '',
    created_at  TEXT    NOT NULL
);

CREATE TABLE IF NOT EXISTS media (
    id            INTEGER PRIMARY KEY AUTOINCREMENT,
    post_id       INTEGER NOT NULL REFERENCES posts(id) ON DELETE CASCADE,
    kind          TEXT    NOT NULL CHECK (kind IN ('image', 'video')),
    filename      TEXT    NOT NULL,
    mime          TEXT    NOT NULL,
    original_name TEXT    NOT NULL DEFAULT '',
    position      INTEGER NOT NULL DEFAULT 0
);

CREATE TABLE IF NOT EXISTS likes (
    post_id   INTEGER NOT NULL REFERENCES posts(id) ON DELETE CASCADE,
    client_id TEXT    NOT NULL,
    PRIMARY KEY (post_id, client_id)
);

CREATE INDEX IF NOT EXISTS idx_media_post ON media(post_id);
CREATE INDEX IF NOT EXISTS idx_likes_post ON likes(post_id);
"""

app = Flask(__name__)
app.config["MAX_CONTENT_LENGTH"] = MAX_FILES * MAX_FILE_BYTES + 1024 * 1024
app.json.sort_keys = False


# --------------------------------------------------------------------------- #
# database
# --------------------------------------------------------------------------- #
def connect() -> sqlite3.Connection:
    os.makedirs(DATA_DIR, exist_ok=True)
    os.makedirs(UPLOAD_DIR, exist_ok=True)
    conn = sqlite3.connect(DB_PATH)
    conn.row_factory = sqlite3.Row
    conn.execute("PRAGMA foreign_keys = ON")
    return conn


def init_db(conn: sqlite3.Connection) -> None:
    conn.executescript(SCHEMA)
    conn.commit()


def get_db() -> sqlite3.Connection:
    if "db" not in g:
        g.db = connect()
    return g.db


@app.teardown_appcontext
def close_db(_exc: BaseException | None) -> None:
    db = g.pop("db", None)
    if db is not None:
        db.close()


# --------------------------------------------------------------------------- #
# helpers
# --------------------------------------------------------------------------- #
def utc_now() -> str:
    return datetime.now(timezone.utc).replace(microsecond=0).isoformat().replace("+00:00", "Z")


def slugify_handle(name: str) -> str:
    slug = re.sub(r"[^a-z0-9_]+", "", name.strip().lower().replace(" ", ""))
    return slug[:24] or "you"


def resolve_media(storage) -> tuple[str, str, str] | None:
    """Return (kind, mime, extension) for an allowed upload, else None."""
    mime = (storage.mimetype or "").lower()
    if mime not in IMAGE_TYPES and mime not in VIDEO_TYPES:
        # Some browsers send application/octet-stream for .mov; fall back to
        # the extension, then confirm through the table above.
        ext = os.path.splitext(storage.filename or "")[1].lower()
        mime = MIME_BY_EXT.get(ext, "")
    if mime in IMAGE_TYPES:
        return "image", mime, IMAGE_TYPES[mime]
    if mime in VIDEO_TYPES:
        return "video", mime, VIDEO_TYPES[mime]
    return None


def serialize_posts(conn: sqlite3.Connection, rows: list[sqlite3.Row]) -> list[dict]:
    if not rows:
        return []
    ids = [row["id"] for row in rows]
    placeholders = ",".join("?" for _ in ids)
    media_rows = conn.execute(
        f"SELECT * FROM media WHERE post_id IN ({placeholders}) ORDER BY post_id, position, id",
        ids,
    ).fetchall()

    media_by_post: dict[int, list[dict]] = {}
    for item in media_rows:
        media_by_post.setdefault(item["post_id"], []).append(
            {
                "id": item["id"],
                "kind": item["kind"],
                "mime": item["mime"],
                "url": f"/media/{item['filename']}",
                "alt": item["original_name"],
            }
        )

    return [
        {
            "id": row["id"],
            "author": {"name": row["author_name"], "handle": row["author_handle"]},
            "text": row["text"],
            "createdAt": row["created_at"],
            "media": media_by_post.get(row["id"], []),
            "likes": {"count": row["like_count"], "liked": bool(row["liked"])},
        }
        for row in rows
    ]


def fetch_posts(conn: sqlite3.Connection, client_id: str, before: int | None, limit: int) -> list[dict]:
    rows = conn.execute(
        """
        SELECT p.*,
               (SELECT COUNT(*) FROM likes l WHERE l.post_id = p.id) AS like_count,
               EXISTS(
                   SELECT 1 FROM likes l2
                   WHERE l2.post_id = p.id AND l2.client_id = ?
               ) AS liked
        FROM posts p
        WHERE (? IS NULL OR p.id < ?)
        ORDER BY p.id DESC
        LIMIT ?
        """,
        (client_id, before, before, limit),
    ).fetchall()
    return serialize_posts(conn, rows)


def load_post(conn: sqlite3.Connection, post_id: int, client_id: str) -> dict | None:
    row = conn.execute(
        """
        SELECT p.*,
               (SELECT COUNT(*) FROM likes l WHERE l.post_id = p.id) AS like_count,
               EXISTS(
                   SELECT 1 FROM likes l2
                   WHERE l2.post_id = p.id AND l2.client_id = ?
               ) AS liked
        FROM posts p WHERE p.id = ?
        """,
        (client_id, post_id),
    ).fetchone()
    if row is None:
        return None
    return serialize_posts(conn, [row])[0]


# --------------------------------------------------------------------------- #
# API
# --------------------------------------------------------------------------- #
@app.get("/api/health")
def health():
    return jsonify({"ok": True, "posts": get_db().execute("SELECT COUNT(*) FROM posts").fetchone()[0]})


@app.get("/api/posts")
def list_posts():
    conn = get_db()
    client_id = (request.args.get("client_id") or "").strip()[:64]

    try:
        limit = int(request.args.get("limit", 6))
    except ValueError:
        return jsonify({"error": "limit must be a number"}), 400
    limit = max(1, min(limit, 20))

    before_raw = request.args.get("before")
    before: int | None = None
    if before_raw:
        try:
            before = int(before_raw)
        except ValueError:
            return jsonify({"error": "before must be a post id"}), 400

    posts = fetch_posts(conn, client_id, before, limit + 1)
    has_more = len(posts) > limit
    posts = posts[:limit]
    next_cursor = posts[-1]["id"] if posts and has_more else None
    return jsonify({"posts": posts, "nextCursor": next_cursor})


@app.post("/api/posts")
def create_post():
    conn = get_db()

    text = (request.form.get("text") or "").strip()
    if len(text) > MAX_TEXT:
        return jsonify({"error": f"Text is limited to {MAX_TEXT} characters."}), 400

    author_name = " ".join((request.form.get("author_name") or "").split())[:40] or "You"
    handle = slugify_handle(author_name)

    uploads = [item for item in request.files.getlist("media") if item and item.filename]
    if len(uploads) > MAX_FILES:
        return jsonify({"error": f"Up to {MAX_FILES} files per post."}), 400
    if not text and not uploads:
        return jsonify({"error": "Add some text, a photo, or a video."}), 400

    saved: list[dict] = []
    for position, storage in enumerate(uploads):
        resolved = resolve_media(storage)
        if resolved is None:
            _cleanup(saved)
            return jsonify({"error": f"Unsupported file type: {storage.filename}"}), 415

        kind, mime, ext = resolved
        filename = f"{uuid.uuid4().hex}{ext}"
        destination = os.path.join(UPLOAD_DIR, filename)
        storage.save(destination)
        if os.path.getsize(destination) > MAX_FILE_BYTES:
            os.remove(destination)
            _cleanup(saved)
            return jsonify({"error": "Each file must be 25 MB or smaller."}), 413

        saved.append(
            {
                "kind": kind,
                "mime": mime,
                "filename": filename,
                "original_name": os.path.basename(storage.filename or "")[:120],
                "position": position,
            }
        )

    try:
        created_at = utc_now()
        cursor = conn.execute(
            "INSERT INTO posts (author_name, author_handle, text, created_at) VALUES (?, ?, ?, ?)",
            (author_name, handle, text, created_at),
        )
        post_id = cursor.lastrowid

        for item in saved:
            conn.execute(
                """INSERT INTO media (post_id, kind, filename, mime, original_name, position)
                   VALUES (?, ?, ?, ?, ?, ?)""",
                (post_id, item["kind"], item["filename"], item["mime"], item["original_name"], item["position"]),
            )
        conn.commit()
    except Exception:
        conn.rollback()
        _cleanup(saved)
        raise

    client_id = (request.form.get("client_id") or "").strip()[:64]
    return jsonify({"post": load_post(conn, post_id, client_id)}), 201


def _cleanup(saved: list[dict]) -> None:
    for item in saved:
        path = os.path.join(UPLOAD_DIR, item["filename"])
        if os.path.exists(path):
            os.remove(path)


@app.post("/api/posts/<int:post_id>/like")
def like_post(post_id: int):
    conn = get_db()
    data = request.get_json(silent=True) or {}
    client_id = str(data.get("client_id") or "").strip()[:64]
    if not client_id:
        return jsonify({"error": "client_id is required"}), 400

    exists = conn.execute("SELECT 1 FROM posts WHERE id = ?", (post_id,)).fetchone()
    if exists is None:
        return jsonify({"error": "Post not found"}), 404

    if data.get("liked"):
        conn.execute("INSERT OR IGNORE INTO likes (post_id, client_id) VALUES (?, ?)", (post_id, client_id))
    else:
        conn.execute("DELETE FROM likes WHERE post_id = ? AND client_id = ?", (post_id, client_id))
    conn.commit()

    count = conn.execute("SELECT COUNT(*) FROM likes WHERE post_id = ?", (post_id,)).fetchone()[0]
    return jsonify({"postId": post_id, "liked": bool(data.get("liked")), "count": count})


@app.get("/media/<path:filename>")
def media(filename: str):
    return send_from_directory(UPLOAD_DIR, filename, conditional=True, max_age=31536000)


@app.errorhandler(RequestEntityTooLarge)
def too_large(_err):
    return jsonify({"error": "That upload is too large (25 MB per file, 6 files)."}), 413


# --------------------------------------------------------------------------- #
# static frontend (only used when `npm run build` has produced frontend/dist)
# --------------------------------------------------------------------------- #
if os.path.isdir(DIST_DIR):

    @app.get("/")
    def index():
        return send_from_directory(DIST_DIR, "index.html")

    @app.get("/<path:path>")
    def spa(path: str):
        candidate = os.path.join(DIST_DIR, path)
        if os.path.isfile(candidate):
            return send_from_directory(DIST_DIR, path)
        return send_from_directory(DIST_DIR, "index.html")


init_db(connect())


if __name__ == "__main__":
    # Production runs through gunicorn (see entrypoint.sh); this is the local
    # server, so debug stays off unless FLASK_DEBUG is set explicitly.
    app.run(
        host="0.0.0.0",
        port=int(os.environ.get("PORT", 5000)),
        debug=os.environ.get("FLASK_DEBUG", "").lower() in {"1", "true", "yes"},
    )
