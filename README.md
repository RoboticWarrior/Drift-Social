# drift

A quiet social feed: scroll through simple posts that can be a photo, a video,
text, or any combination of the three. Post your own, like other people's.

- **Frontend:** React 19 + Vite (plain JavaScript, no TypeScript)
- **Backend:** Python Flask + SQLite
- **Media:** uploaded files stored on disk, served by Flask with HTTP range
  support so videos stream and seek properly

## Run it

Two processes: Flask on `:5000`, Vite on `:3000`. Vite proxies `/api` and
`/media` to Flask, so the browser only talks to one origin.

```bash
# terminal 1 — API
cd backend
pip install -r requirements.txt
python3 seed.py        # optional: 12 demo posts with generated photos/video
python3 app.py         # http://localhost:5000

# terminal 2 — app
cd frontend
npm install
npm run dev            # http://localhost:3000
```

Open <http://localhost:3000>. The feed loads six posts at a time and appends
more as you scroll.

### Single-process mode

```bash
cd frontend && npm run build     # writes frontend/dist
cd ../backend && python3 app.py  # Flask serves the built app at :5000
```

## What the app does

- **Composer** at the top of the feed: text plus up to 6 photos/videos, upload
  progress, per-file previews, editable display name (remembered in
  `localStorage`), `⌘/Ctrl + Enter` to post.
- **Feed** with infinite scroll (`IntersectionObserver`), skeletons, empty and
  end-of-feed states, and an error state with retry.
- **Posts** render text, a single photo, a 2-up or 3-up media grid (first tile
  spans the row when the count is odd), and videos with native controls.
  Photos open in a lightbox; `Esc` closes it.
- **Likes** are optimistic and persisted per browser through a `client_id`
  stored in `localStorage`.
- Responsive down to small phones, and it honours `prefers-reduced-motion`.

## API

| Method | Path | Notes |
| --- | --- | --- |
| `GET` | `/api/posts?limit=6&before=<id>&client_id=<id>` | Newest first, cursor-paginated. Returns `{ posts, nextCursor }`. |
| `POST` | `/api/posts` | `multipart/form-data`: `text`, `author_name`, optional `media` files (repeatable). Returns `201 { post }`. |
| `POST` | `/api/posts/<id>/like` | JSON `{ client_id, liked }`. Idempotent. Returns `{ postId, liked, count }`. |
| `GET` | `/media/<filename>` | Uploaded file, cached, byte-range supported. |
| `GET` | `/api/health` | `{ ok: true, posts: n }`. |

### Validation

- Text up to 2000 characters; a post needs text or media.
- Up to 6 files per post, 25 MB each.
- Accepted types: `jpeg`, `png`, `gif`, `webp`, `mp4`, `webm`, `mov`. The
  stored extension is chosen server-side from the detected MIME type, so an
  upload can never be served back as HTML.

## Storage

- `backend/data/app.db` — SQLite (`posts`, `media`, `likes`)
- `backend/uploads/` — uploaded media

Both are gitignored. Delete `backend/data/app.db` and `backend/uploads/*`, then
run `python3 seed.py` again to reset the demo feed.

The seed script draws its images with Pillow, and renders demo videos with
ffmpeg if one is on `PATH` (otherwise those two posts are skipped and the feed
is images + text only).
