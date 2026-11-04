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

## Deploy on Fly.io

The repo ships a `Dockerfile` (multi-stage: Vite build, then Python 3.12 +
gunicorn), a `fly.toml`, and an `entrypoint.sh` that seeds the demo feed once
per volume and then starts gunicorn.

```bash
fly apps create <your-app-name>          # then set `app` in fly.toml
fly volumes create drift_data --size 1 --region iad
fly deploy
fly open
```

The database and uploaded media live under `/data`, which is a persistent
volume, so they survive deploys and restarts. A volume is attached to exactly
one machine, so keep this app at a single instance. `auto_stop_machines` lets
it sleep when idle; the first request after a sleep takes a few seconds, and
`fly logs` streams the access log.

- `SEED_DEMO=0` starts with an empty feed instead of the demo posts.
- `STORAGE_DIR` moves the data directory (defaults to `/data` in the image,
  `backend/` when running locally).
- The image contains no ffmpeg, so a fresh volume is seeded with photos, an
  animated GIF and text. Add `apt-get install -y ffmpeg` to the Dockerfile if
  you also want the two seeded video posts.

## Deploy on a free VM (Oracle Cloud Always Free)

The same `Dockerfile` runs anywhere Docker does. A `docker-compose.yml` at the
repo root builds the image, keeps the database and uploads in `./data`, and
publishes the app on `127.0.0.1:8080` behind nginx.

Oracle's Always Free tier gives an Ampere ARM VM with 2 OCPU / 12 GB RAM and
200 GB of block storage, which is enough for a real media feed. The full
walkthrough — VM shape, Security List rules, the guest firewall gotcha, TLS —
is in [`deploy/oracle/README.md`](deploy/oracle/README.md).

```bash
# on the VM, after cloning this repo
sudo DOMAIN=drift.example.com EMAIL=you@example.com ./deploy/oracle/bootstrap.sh
```

Subsequent deploys are `./deploy/oracle/update.sh` (git pull, rebuild, health
check).

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

Both are gitignored. Set `STORAGE_DIR` to relocate them (the Docker image
points it at `/data`, so a mounted volume holds both).

To reset the demo feed, delete `backend/data/app.db` and `backend/uploads/*`,
then run `python3 seed.py` again.

The seed script draws its images with Pillow, and renders demo videos with
ffmpeg if one is on `PATH` (otherwise those two posts are skipped and the feed
is images + text only).
