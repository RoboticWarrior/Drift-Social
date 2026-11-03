"""Populate the feed with demo posts and generated media.

Run once:  python3 seed.py
Images are drawn with Pillow; a short demo video is produced with ffmpeg when
one is available (system ffmpeg or the imageio-ffmpeg wheel).
"""

from __future__ import annotations

import math
import os
import random
import shutil
import subprocess
import sys
import tempfile
import uuid
from datetime import datetime, timedelta, timezone

from PIL import Image, ImageDraw, ImageFilter

from app import DB_PATH, UPLOAD_DIR, connect, init_db

SEED_CLIENT_TAG = "seed"
random.seed(7)

PALETTES = [
    ((255, 148, 92), (188, 74, 143), (58, 34, 96)),
    ((24, 98, 160), (35, 187, 173), (9, 28, 54)),
    ((255, 209, 102), (240, 113, 103), (59, 47, 92)),
    ((123, 97, 255), (67, 206, 162), (16, 22, 44)),
    ((250, 130, 175), (94, 96, 206), (20, 18, 45)),
    ((255, 183, 94), (255, 96, 128), (29, 20, 48)),
]


# --------------------------------------------------------------------------- #
# media generation
# --------------------------------------------------------------------------- #
def _gradient(size: tuple[int, int], palette: tuple, shift: float = 0.0) -> Image.Image:
    width, height = size
    top, middle, bottom = palette
    base = Image.new("RGB", (width, height))
    pixels = base.load()
    for y in range(height):
        t = y / max(height - 1, 1)
        if t < 0.55:
            k = t / 0.55
            a, b = top, middle
        else:
            k = (t - 0.55) / 0.45
            a, b = middle, bottom
        color = tuple(int(a[i] + (b[i] - a[i]) * k) for i in range(3))
        for x in range(width):
            wobble = math.sin((x / width) * math.pi + shift) * 10
            pixels[x, y] = tuple(max(0, min(255, int(c + wobble))) for c in color)
    return base


def make_art(palette: tuple, size: tuple[int, int] = (1200, 900), shift: float = 0.0) -> Image.Image:
    image = _gradient(size, palette, shift).convert("RGBA")

    glow = Image.new("RGBA", size, (0, 0, 0, 0))
    draw = ImageDraw.Draw(glow)
    for _ in range(5):
        radius = random.randint(size[0] // 9, size[0] // 4)
        cx = random.randint(0, size[0])
        cy = random.randint(0, size[1])
        tint = random.choice(palette)
        draw.ellipse(
            [cx - radius, cy - radius, cx + radius, cy + radius],
            fill=(*tint, random.randint(45, 95)),
        )
    glow = glow.filter(ImageFilter.GaussianBlur(radius=size[0] // 22))
    image = Image.alpha_composite(image, glow)

    shapes = Image.new("RGBA", size, (0, 0, 0, 0))
    sdraw = ImageDraw.Draw(shapes)
    for _ in range(random.randint(3, 6)):
        w = random.randint(size[0] // 12, size[0] // 3)
        h = random.randint(size[1] // 12, size[1] // 2)
        x = random.randint(-w // 3, size[0] - w // 2)
        y = random.randint(-h // 3, size[1] - h // 2)
        if random.random() < 0.5:
            sdraw.rounded_rectangle([x, y, x + w, y + h], radius=w // 6, fill=(255, 255, 255, random.randint(12, 30)))
        else:
            sdraw.polygon(
                [(x, y), (x + w, y + h // 3), (x + w // 3, y + h)],
                fill=(255, 255, 255, random.randint(10, 26)),
            )
    image = Image.alpha_composite(image, shapes)

    image = image.convert("RGB")

    vignette = Image.new("L", size, 0)
    vdraw = ImageDraw.Draw(vignette)
    vdraw.ellipse([-size[0] // 3, -size[1] // 3, size[0] + size[0] // 3, size[1] + size[1] // 3], fill=90)
    vignette = vignette.filter(ImageFilter.GaussianBlur(radius=size[0] // 10))
    dark = Image.new("RGB", size, (0, 0, 0))
    return Image.composite(image, dark, vignette.point(lambda v: 120 + int(v * 1.2)))


def save_image(palette: tuple, size=(1200, 900), animated: bool = False, shift: float = 0.0) -> tuple[str, str]:
    """Write an image into uploads/ and return (filename, mime)."""
    if animated:
        frames = []
        for i in range(16):
            frame = make_art(palette, (720, 540), shift=i * 0.45)
            frames.append(frame)
        filename = f"{uuid.uuid4().hex}.gif"
        frames[0].save(
            os.path.join(UPLOAD_DIR, filename),
            save_all=True,
            append_images=frames[1:],
            duration=110,
            loop=0,
            optimize=True,
        )
        return filename, "image/gif"

    image = make_art(palette, size, shift)
    filename = f"{uuid.uuid4().hex}.jpg"
    image.save(os.path.join(UPLOAD_DIR, filename), quality=82, optimize=True, progressive=True)
    return filename, "image/jpeg"


def find_ffmpeg() -> str | None:
    found = shutil.which("ffmpeg")
    if found:
        return found
    try:
        import imageio_ffmpeg  # type: ignore

        return imageio_ffmpeg.get_ffmpeg_exe()
    except Exception:
        return None


def save_video(palette: tuple) -> tuple[str, str] | None:
    ffmpeg = find_ffmpeg()
    if not ffmpeg:
        return None

    size = (960, 540)
    fps = 24
    seconds = 5
    with tempfile.TemporaryDirectory() as tmp:
        for index in range(fps * seconds):
            frame = make_art(palette, size, shift=index * 0.09)
            frame.save(os.path.join(tmp, f"f{index:04d}.jpg"), quality=88)
        filename = f"{uuid.uuid4().hex}.mp4"
        destination = os.path.join(UPLOAD_DIR, filename)
        try:
            subprocess.run(
                [
                    ffmpeg, "-y", "-loglevel", "error",
                    "-framerate", str(fps),
                    "-i", os.path.join(tmp, "f%04d.jpg"),
                    "-c:v", "libx264", "-pix_fmt", "yuv420p",
                    "-preset", "medium", "-crf", "26",
                    "-movflags", "+faststart",
                    destination,
                ],
                check=True,
                capture_output=True,
            )
        except Exception as exc:  # noqa: BLE001 - seeding should never fail hard
            print(f"  ! video seed skipped ({exc})", file=sys.stderr)
            return None
    return filename, "video/mp4"


# --------------------------------------------------------------------------- #
# posts
# --------------------------------------------------------------------------- #
PROFILES = {
    "maya": ("Maya Ortiz", "maya"),
    "tomas": ("Tomás Rivera", "tomas"),
    "lena": ("Lena Fields", "lena"),
    "arjun": ("Arjun Mehta", "arjun"),
    "sana": ("Sana Iqbal", "sana"),
    "noah": ("Noah Berg", "noah"),
    "iris": ("Iris Adeyemi", "iris"),
    "kai": ("Kai Nakamura", "kai"),
}


def build_posts(video: tuple[str, str] | None) -> list[dict]:
    images = [save_image(palette, shift=i * 0.6) for i, palette in enumerate(PALETTES[:5])]
    loop = save_image(PALETTES[2], animated=True)

    posts: list[dict] = []

    def add(profile: str, text: str, media: list[tuple[str, str]] | None = None) -> None:
        name, handle = PROFILES[profile]
        posts.append({"name": name, "handle": handle, "text": text, "media": media or []})

    add(
        "maya",
        "spent the morning rewriting a function i wrote last year. it's four lines now.\n\n"
        "i have never felt so powerful",
    )
    add("tomas", "golden hour from the roof, no filter needed", [(images[0][0], "image", images[0][1])])
    add(
        "lena",
        "three days offline in the mountains. phone stayed in the bag the whole time",
        [
            (images[1][0], "image", images[1][1]),
            (images[2][0], "image", images[2][1]),
            (images[3][0], "image", images[3][1]),
        ],
    )
    if video:
        add("arjun", "six seconds of the sea doing its thing 🌊", [(video[0], "video", video[1])])
    add(
        "sana",
        "unpopular opinion: the best part of any project is deleting code, not writing it.",
    )
    add("noah", "my desk at 2am. yes, the mug is from 2019", [(images[4][0], "image", images[4][1])])
    add(
        "kai",
        "made a tiny loop in my lunch break. it's not much but it's mine",
        [(loop[0], "image", loop[1])],
    )
    if video:
        add(
            "iris",
            "took the long way home just to watch the light change",
            [(video[0], "video", video[1])],
        )
    add(
        "iris",
        "reminder that you can just make things. nobody has to approve it first.",
    )
    add(
        "maya",
        "coffee, a notebook, and absolutely no plan for the afternoon. ideal saturday",
        [
            (images[2][0], "image", images[2][1]),
            (images[0][0], "image", images[0][1]),
        ],
    )
    add(
        "tomas",
        "the city is so much quieter at 7am. i should know, i got up early exactly once.",
    )
    add("arjun", "colour study #14", [(images[3][0], "image", images[3][1])])
    return posts


def main() -> None:
    os.makedirs(UPLOAD_DIR, exist_ok=True)
    conn = connect()
    init_db(conn)

    if conn.execute("SELECT COUNT(*) FROM posts").fetchone()[0] > 0:
        print("Database already has posts — nothing seeded. Delete data/app.db to reseed.")
        return

    print("generating demo media…")
    video = save_video(PALETTES[4])
    if video is None:
        print("  (ffmpeg not found — seeding images and text only)")

    posts = build_posts(video)
    now = datetime.now(timezone.utc).replace(microsecond=0)

    offsets = [
        22, 95, 190, 260, 340, 430, 520, 700, 900, 1200, 1500, 1800,
    ]

    for index, post in enumerate(posts):
        created = (now - timedelta(minutes=offsets[index % len(offsets)])).isoformat().replace("+00:00", "Z")
        cursor = conn.execute(
            "INSERT INTO posts (author_name, author_handle, text, created_at) VALUES (?, ?, ?, ?)",
            (post["name"], post["handle"], post["text"], created),
        )
        post_id = cursor.lastrowid
        for position, (filename, kind, mime) in enumerate(post["media"]):
            conn.execute(
                """INSERT INTO media (post_id, kind, filename, mime, original_name, position)
                   VALUES (?, ?, ?, ?, ?, ?)""",
                (post_id, kind, filename, mime, "", position),
            )

        for liker in random.sample(range(1, 60), random.randint(0, 26)):
            conn.execute(
                "INSERT OR IGNORE INTO likes (post_id, client_id) VALUES (?, ?)",
                (post_id, f"{SEED_CLIENT_TAG}-{liker}"),
            )

    conn.commit()
    conn.close()
    print(f"seeded {len(posts)} posts into {DB_PATH}")


if __name__ == "__main__":
    main()
