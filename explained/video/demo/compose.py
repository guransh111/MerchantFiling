"""Builds the dashboard demo film frame by frame from the captures (capture.js, endcard.js).

The camera (scroll, zoom, focus), the cursor and the clicks are keyframed per scene in SCENES below, in seconds of
demo time (0 = the start of the demo, right after the intro film). To sync to a new voiceover, change the times
there and re-run:
    python compose.py <capture dir> <out.mp4> [fps]
Every frame is composed in Python and piped to ffmpeg, so motion is perfectly smooth at any frame rate.
"""
from __future__ import annotations

import json
import math
import subprocess
import sys
from functools import lru_cache
from pathlib import Path

from PIL import Image, ImageDraw

CAP = Path(sys.argv[1])
OUT = sys.argv[2]
FPS = int(sys.argv[3]) if len(sys.argv) > 3 else 60
W, H = 1920, 1080
DSF = 1.5                       # captures are 1.5x for sharp zooms
META = json.loads((CAP / "meta.json").read_text())
SIDE_W = 281                    # sidebar width in CSS px


# ------------------------------------------------------------------ easing
def clamp(x, a=0.0, b=1.0):
    return max(a, min(b, x))


def ease_io(x):                 # slow, fast, slow (cubic)
    x = clamp(x)
    return 4 * x * x * x if x < 0.5 else 1 - (-2 * x + 2) ** 3 / 2


def ease_out(x):                # fast start, soft landing (expo)
    x = clamp(x)
    return 1 if x >= 1 else 1 - 2 ** (-10 * x)


def track(keys, t, ease=ease_io):
    """keys: [(time, value or tuple)]: holds before the first and after the last; eased between."""
    if t <= keys[0][0]:
        return keys[0][1]
    for (t0, v0), (t1, v1) in zip(keys, keys[1:]):
        if t <= t1:
            u = ease((t - t0) / (t1 - t0)) if t1 > t0 else 1
            if isinstance(v0, tuple):
                return tuple(a + (b - a) * u for a, b in zip(v0, v1))
            return v0 + (v1 - v0) * u
    return keys[-1][1]


# ------------------------------------------------------------------ scenes
def nav(label, page="overview"):
    x, y, w, h = META[page]["nav"][label]
    return (x + 70, y + h / 2)          # a point on the menu item's label


def b(page, key, fx=0.5, fy=0.5):
    x, y, w, h = META[page]["boxes"][key]
    return (x + w * fx, y + h * fy)


Z1 = (1.0, 960.0, 540.0)            # camera at rest: zoom 1, centred
# camera keys: (t, (scrollY, zoom, focusX, focusY)); focus is in viewport px; cursor keys: (t, (x, y_page)); clicks: [t]
SCENES = [
    dict(page="home", start=0.0, end=8.0, anim=(0.4, None),
         cam=[(0, (0, *Z1))],
         cursor=[(0, (1500, 900)), (6.9, (1500, 900)), (7.7, nav("Overview"))], clicks=[7.8]),
    dict(page="overview", start=8.0, end=14.0,
         cam=[(8.2, (0, *Z1)), (9.4, (0, 1.32, *b("overview", "funnel", 0.5, 0.45))), (12.4, (0, 1.32, *b("overview", "funnel", 0.5, 0.45))),
              (13.2, (0, *Z1))],
         cursor=[(8.0, nav("Overview")), (9.2, b("overview", "funnel", 0.12, 0.45)), (10.4, b("overview", "funnel", 0.37, 0.45)),
                 (11.4, b("overview", "funnel", 0.62, 0.45)), (12.3, b("overview", "funnel", 0.88, 0.45)), (13.6, nav("Risk queue"))], clicks=[13.7]),
    dict(page="queue", start=14.0, end=19.0,
         cam=[(14.3, (0, *Z1)), (15.4, (0, 1.4, *b("queue", "table", 0.78, 0.35))), (17.6, (0, 1.4, *b("queue", "table", 0.78, 0.35))), (18.3, (0, *Z1))],
         cursor=[(14.0, nav("Risk queue")), (15.4, b("queue", "table", 0.72, 0.09)), (17.0, b("queue", "table", 0.72, 0.2)), (18.6, nav("Merchant drill-down"))],
         clicks=[18.7]),
    dict(page="merchant", start=19.0, end=31.0,
         cam=[(19.3, (0, *Z1)), (20.4, (0, 1.32, *b("merchant", "head"))), (22.4, (0, 1.32, *b("merchant", "head"))),
              (23.6, (470, *Z1)), (24.6, (470, 1.75, 840, 664 - 470 + 70)), (26.8, (470, 1.75, 840, 664 - 470 + 70)),
              (27.8, (470, 1.75, 840, 801 - 470 + 70)), (29.4, (470, 1.75, 840, 801 - 470 + 70)), (30.2, (470, *Z1))],
         cursor=[(19.0, nav("Merchant drill-down")), (20.4, b("merchant", "head", 0.86, 0.45)), (22.6, b("merchant", "head", 0.86, 0.45)),
                 (24.6, (720, 664 + 52)), (26.6, (870, 664 + 52)), (27.8, (720, 801 + 52)), (29.4, (790, 801 + 52)), (30.4, nav("Network"))],
         clicks=[30.5]),
    dict(page="network", start=31.0, end=39.0,
         cam=[(31.2, (0, *Z1)), (32.6, (560, *Z1)), (33.6, (560, 1.18, 1100, 520)), (37.0, (560, 1.18, 1100, 520)), (37.8, (560, *Z1))],
         cursor=[(31.0, nav("Network")), (33.6, (850, 768)), (34.8, (1252, 832)), (36.0, (1001, 1106)), (37.0, (1001, 1106)), (38.2, nav("Scan a betting page"))],
         clicks=[38.3]),
    dict(page="scan0", start=39.0, end=40.6,
         cam=[(39.0, (0, *Z1))],
         cursor=[(39.0, nav("Scan a betting page")), (40.1, b("scan0", "button"))], clicks=[40.2]),
    dict(page="scan1", start=40.6, end=47.0, fade=0.25,
         cam=[(40.8, (0, *Z1)), (41.9, (0, 1.32, 1101, 690)), (45.2, (0, 1.32, 1101, 690)), (46.0, (0, *Z1))],
         cursor=[(40.6, b("scan0", "button")), (42.2, b("scan1", "found", 0.03, 0.5)), (44.6, b("scan1", "found", 0.22, 0.5)), (46.2, nav("Case management"))],
         clicks=[46.3]),
    dict(page="cases", start=47.0, end=56.0,
         cam=[(47.2, (0, *Z1)), (48.4, (0, 1.42, *b("cases", "clock"))), (50.8, (0, 1.42, *b("cases", "clock"))),
              (52.2, (1010, *Z1)), (53.2, (1010, 1.15, 1180, 560)), (54.4, (1010, 1.15, 1180, 560)), (55.1, (1010, *Z1))],
         cursor=[(47.0, nav("Case management")), (48.4, b("cases", "clock", 0.55, 0.35)), (50.6, b("cases", "clock", 0.55, 0.62)),
                 (53.2, (760, 1148 + 230)), (54.4, (900, 1148 + 230)), (55.4, nav("Customer's payment screen"))],
         clicks=[55.5]),
    dict(page="payer", start=56.0, end=63.0,
         cam=[(56.2, (0, *Z1)), (57.5, (0, 1.65, 1101, 420)), (61.4, (0, 1.65, 1101, 420)), (62.2, (0, *Z1))],
         cursor=[(56.0, nav("Customer's payment screen")), (57.6, b("payer", "warn", 0.9, 1.25)), (61.4, b("payer", "warn", 0.9, 1.25)), (62.4, nav("Home"))],
         clicks=[62.5]),
    dict(page="home", start=63.0, end=66.4, anim=(63.2, None),
         cam=[(63.0, (0, *Z1))],
         cursor=[(63.0, nav("Home")), (64.4, (1500, 900))], clicks=[]),
    dict(page="endcard", start=66.4, end=72.0, fade=0.5),
]
TOTAL = SCENES[-1]["end"]


# ------------------------------------------------------------------ images
@lru_cache(maxsize=None)
def load(name):
    return Image.open(CAP / name).convert("RGB")


@lru_cache(maxsize=64)
def viewport(page, scroll):
    """The page as seen at a scroll offset (CSS px), with the fixed sidebar on top, at capture resolution."""
    full = load(f"{page}_full.png")
    y = int(round(scroll * DSF))
    y = max(0, min(y, full.height - int(H * DSF)))
    img = full.crop((0, y, full.width, y + int(H * DSF))).copy()
    side = load(f"{page}_view.png").crop((0, 0, int(SIDE_W * DSF), int(H * DSF)))
    img.paste(side, (0, 0))
    return img


def home_anim_frame(t_anim):
    frames = sorted((CAP / "home_anim").glob("*.png"))
    i = int(clamp(t_anim * 60, 0, len(frames) - 1))
    return load(f"home_anim/{frames[i].name}")


def endcard_frame(t):
    frames = sorted((CAP / "endcard").glob("*.png"))
    i = int(clamp(t * 60, 0, len(frames) - 1))
    return load(f"endcard/{frames[i].name}")


# cursor sprite: a clean arrow, drawn at 4x and scaled down for smooth edges
def make_cursor(size=30):
    S = 4
    pts = [(0, 0), (0, 22), (5.5, 17), (9.5, 26), (13, 24.5), (9, 15.8), (16, 15.8)]
    img = Image.new("RGBA", (int(20 * S), int(30 * S)), (0, 0, 0, 0))
    d = ImageDraw.Draw(img)
    p = [(x * S + 2 * S, y * S + 2 * S) for x, y in pts]
    d.polygon(p, fill=(20, 20, 22, 255))
    inner = [(x * S + 2 * S, y * S + 2 * S) for x, y in [(1.6, 3.6), (1.6, 18.4), (5.9, 14.4), (10, 22.7), (11.1, 22.2), (7.2, 14.2), (12.6, 14.2)]]
    d.polygon(inner, fill=(244, 244, 245, 255))
    k = size / 30
    return img.resize((int(img.width * k / S), int(img.height * k / S)), Image.LANCZOS)


CURSOR = make_cursor(32)


def camera_at(scene, t):
    return track(scene["cam"], t) if "cam" in scene else (0, *Z1)


def render_scene(scene, t):
    """One frame of a scene at demo time t, as a 1920x1080 RGB image."""
    page = scene["page"]
    if page == "endcard":
        return endcard_frame(t - scene["start"]).copy()
    scroll, z, fx, fy = camera_at(scene, t)
    if "anim" in scene:
        base = home_anim_frame(t - scene["anim"][0])
    else:
        base = viewport(page, round(scroll))
    # zoom: a crop of the viewport centred on the focus, kept inside the frame
    cw, ch = W / z, H / z
    x0 = clamp(fx - cw / 2, 0, W - cw)
    y0 = clamp(fy - ch / 2, 0, H - ch)
    box = tuple(int(round(v * DSF)) for v in (x0, y0, x0 + cw, y0 + ch))
    frame = base.crop(box).resize((W, H), Image.BICUBIC)
    # cursor and clicks, mapped through the camera
    if "cursor" in scene:
        # cursor keys are page points; turn each into a viewport point using the scroll at that key's time
        # (the sidebar doesn't scroll), then move between them, so crossing into the sidebar never jumps
        keys = [(tk, (x, y - camera_at(scene, tk)[0] if x > SIDE_W else y)) for tk, (x, y) in scene["cursor"]]
        cx, cy = track(keys, t)
        sx, sy = (cx - x0) * z, (cy - y0) * z
        draw = ImageDraw.Draw(frame, "RGBA")
        for tc in scene.get("clicks", []):
            u = (t - tc) / 0.45
            if 0 <= u <= 1:
                r = 8 + 26 * ease_out(u)
                a = int(150 * (1 - u))
                draw.ellipse((sx - r, sy - r, sx + r, sy + r), outline=(244, 244, 245, a), width=3)
        press = any(0 <= t - tc <= 0.12 for tc in scene.get("clicks", []))
        cur = CURSOR if not press else CURSOR.resize((int(CURSOR.width * 0.9), int(CURSOR.height * 0.9)), Image.LANCZOS)
        frame.paste(cur, (int(sx - 2), int(sy - 2)), cur)
    return frame


def render(t):
    cur = next((s for s in SCENES if s["start"] <= t < s["end"]), SCENES[-1])
    img = render_scene(cur, t)
    fade = cur.get("fade", 0.3)
    i = SCENES.index(cur)
    if i > 0 and t - cur["start"] < fade:       # crossfade from the previous scene's last moment
        prev = SCENES[i - 1]
        img = Image.blend(render_scene(prev, prev["end"] - 1e-3), img, ease_io((t - cur["start"]) / fade))
    return img


def main():
    n = int(round(TOTAL * FPS))
    ff = subprocess.Popen(["ffmpeg", "-y", "-loglevel", "error", "-f", "rawvideo", "-pix_fmt", "rgb24", "-s", f"{W}x{H}", "-r", str(FPS),
                           "-i", "-", "-c:v", "libx264", "-preset", "slow", "-crf", "15", "-pix_fmt", "yuv420p", "-movflags", "+faststart", OUT],
                          stdin=subprocess.PIPE)
    for k in range(n):
        ff.stdin.write(render(k / FPS).tobytes())
        if k % (FPS * 10) == 0:
            print(f"{k / FPS:5.1f}s / {TOTAL:.0f}s", flush=True)
    ff.stdin.close()
    ff.wait()
    print("wrote", OUT)


if __name__ == "__main__":
    if len(sys.argv) > 4 and sys.argv[4] == "--stills":
        out = Path(OUT)
        out.mkdir(exist_ok=True)
        for t in [float(x) for x in sys.argv[5].split(",")]:
            render(t).save(out / f"s_{t:05.1f}.jpg", quality=88)
    else:
        main()
