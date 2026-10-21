"""
Xubair for Windows — a sarcastic goblin who lives on your desktop.
Run: python xubair_win.py
"""
import tkinter as tk
from PIL import Image, ImageTk, ImageDraw, ImageFont
import os, sys, random, math, json

# ── Config ────────────────────────────────────────────────────────────────────

TRANSPARENT    = "#FF00FF"
TRANSPARENT_T  = (255, 0, 255, 255)
TARGET_HEIGHT  = 120          # character height in pixels
FPS            = 24
WALK_SPEED     = 1.8          # px / frame
GRAVITY        = 1.2
BOUNCE         = 0.45
CANVAS_W       = 360
CANVAS_H       = 220          # bubble area + character

IDLE_LINES = [
    "I know I'm in a window. I can see the edges.",
    "Your wallpaper is a choice.",
    "I don't pay rent. I have no regrets.",
    "This pixel is my corner. Find your own.",
    "I've been here longer than your last project.",
    "Fascinating. You moved the mouse.",
    "I'm not ignoring you. I'm just not engaging.",
    "My lawyer says I don't have to move.",
    "Oh look. It's you again.",
    "I've seen better wallpapers. Just saying.",
    "Don't look at me like that.",
    "I'm aware of the taskbar. I choose not to acknowledge it.",
    "Still here.",
    "You can't evict me. I checked.",
    "I was napping. This better be important.",
    "Whatever you're about to do, I disapprove.",
    "Seven windows open. Classic.",
    "Clocked in. No intention of leaving.",
    "I see you typing. Riveting.",
    "If I were paid per sigh, I'd retire.",
    "The audacity of this RAM usage.",
    "I've decided not to comment. And yet.",
]

POKE_LINES = [
    "OW.",
    "Was that necessary?",
    "I'm logging this.",
    "You have too much time.",
    "Stop.",
    "I felt that.",
    "Impressive. Very mature.",
    "Again? Really?",
    "I could sue. In 47 jurisdictions.",
    "Do you do this to everyone?",
    "That's assault.",
    "Bold choice.",
]

EDGE_LINES = [
    "...the edge again.",
    "Glass wall. Of course.",
    "Solid boundary. Noted.",
    "I walked into that one.",
]

# ── Resource path (dev + PyInstaller bundle) ──────────────────────────────────

def resource_path(*parts):
    base = getattr(sys, "_MEIPASS", os.path.dirname(os.path.abspath(__file__)))
    return os.path.join(base, *parts)

# ── Sprite loading + compositing ──────────────────────────────────────────────

def load_sprites():
    sprites_dir = resource_path("Sprites")
    meta_path = os.path.join(sprites_dir, "sprites.json")
    with open(meta_path) as f:
        meta = json.load(f)["sprites"]
    loaded = {}
    for name, info in meta.items():
        path = os.path.join(sprites_dir, info["file"])
        if os.path.exists(path):
            loaded[name] = {"img": Image.open(path).convert("RGBA"), "meta": info}
    return loaded


def compose(sprites, body_key, face_key, target_h):
    body_info = sprites.get(body_key)
    if body_info is None:
        return None
    body_img  = body_info["img"]
    body_meta = body_info["meta"]
    s = target_h / body_img.height
    body_scaled = body_img.resize(
        (round(body_img.width * s), target_h), Image.LANCZOS
    )

    face_info = sprites.get(face_key)
    if face_info is None or "faceBox" not in body_meta:
        return body_scaled

    face_img  = face_info["img"]
    face_meta = face_info["meta"]
    if "faceBox" not in face_meta:
        return body_scaled

    bfx, bfy, bfw, bfh = body_meta["faceBox"]
    ffx, ffy, ffw, ffh  = face_meta["faceBox"]

    fs = (bfw * s) / ffw                              # face scale factor
    face_scaled = face_img.resize(
        (round(face_img.width * fs), round(face_img.height * fs)), Image.LANCZOS
    )

    body_cx = (bfx + bfw / 2) * s
    body_cy = (bfy + bfh / 2) * s
    face_cx = (ffx + ffw / 2) * fs
    face_cy = (ffy + ffh / 2) * fs

    px = round(body_cx - face_cx)
    py = round(body_cy - face_cy)

    result = body_scaled.copy()
    result.paste(face_scaled, (px, py), face_scaled)
    return result


def to_rgb(rgba_img):
    """Composite RGBA onto magenta background for colour-key transparency."""
    bg = Image.new("RGBA", rgba_img.size, TRANSPARENT_T)
    return Image.alpha_composite(bg, rgba_img).convert("RGB")


def build_cache(sprites):
    cache = {}
    faces = [k for k in sprites if k.startswith("face_")]
    if not faces:
        faces = [None]

    for face in faces:
        for body_key, slot in [("body_front", "front"), ("body_side", "side")]:
            if body_key not in sprites:
                continue
            img = compose(sprites, body_key, face or "", TARGET_HEIGHT)
            if img is None:
                continue
            img_r = to_rgb(img)
            img_l = to_rgb(img.transpose(Image.FLIP_LEFT_RIGHT))
            cache[(face, slot, "right")] = img_r
            cache[(face, slot, "left")]  = img_l

    if "body_back" in sprites:
        bd = sprites["body_back"]["img"]
        s  = TARGET_HEIGHT / bd.height
        bk = bd.resize((round(bd.width * s), TARGET_HEIGHT), Image.LANCZOS)
        cache[(None, "back", "right")] = to_rgb(bk)
        cache[(None, "back", "left")]  = to_rgb(bk.transpose(Image.FLIP_LEFT_RIGHT))

    return cache, faces


# ── Speech bubble ─────────────────────────────────────────────────────────────

def make_bubble(text, max_w=240):
    try:
        font = ImageFont.truetype("arial.ttf", 13)
    except Exception:
        font = ImageFont.load_default()

    dummy = Image.new("RGB", (1, 1))
    d     = ImageDraw.Draw(dummy)

    words, lines, line = text.split(), [], []
    for w in words:
        test = " ".join(line + [w])
        bx   = d.textbbox((0, 0), test, font=font)
        if bx[2] > max_w - 20 and line:
            lines.append(" ".join(line))
            line = [w]
        else:
            line.append(w)
    if line:
        lines.append(" ".join(line))

    lh   = 18
    pad  = 10
    tw   = max(d.textbbox((0, 0), l, font=font)[2] for l in lines)
    bw   = tw + pad * 2
    bh   = len(lines) * lh + pad * 2 + 10

    img = Image.new("RGBA", (bw + 4, bh + 4), (0, 0, 0, 0))
    dr  = ImageDraw.Draw(img)
    dr.rounded_rectangle([2, 2, bw + 2, bh - 8], radius=8,
                          fill=(240, 240, 230, 235), outline=(80, 80, 60, 200), width=1)
    tx = bw // 2
    dr.polygon([(tx-6, bh-8), (tx+6, bh-8), (tx, bh+4)],
               fill=(240, 240, 230, 235), outline=(80, 80, 60, 200))
    for i, l in enumerate(lines):
        dr.text((pad + 2, pad + 2 + i * lh), l, fill=(30, 30, 20, 255), font=font)
    return img

# ── Main app ──────────────────────────────────────────────────────────────────

class XubairApp:
    def __init__(self):
        self.root = tk.Tk()
        self.root.overrideredirect(True)
        self.root.wm_attributes("-topmost", True)
        self.root.wm_attributes("-transparentcolor", TRANSPARENT)
        self.root.configure(bg=TRANSPARENT)

        self.sw = self.root.winfo_screenwidth()
        self.sh = self.root.winfo_screenheight()

        # position: character feet at (x, y) in screen coords
        self.x = float(self.sw // 2)
        self.y = float(self.sh - 60)   # above taskbar
        self.vx = WALK_SPEED
        self.vy = 0.0
        self.on_ground = True

        self.state       = "idle"   # idle | walking | talking
        self.frame_n     = 0
        self.bob_phase   = 0.0

        self.bubble_text  = None
        self.bubble_ticks = 0
        self.last_line    = ""

        self.sprites = load_sprites()
        self.cache, self.faces = build_cache(self.sprites)
        self.face = self.faces[0] if self.faces else None

        self.canvas = tk.Canvas(
            self.root, width=CANVAS_W, height=CANVAS_H,
            bg=TRANSPARENT, highlightthickness=0, bd=0
        )
        self.canvas.pack()
        self._set_window_pos()

        self._drag_ox = 0
        self._drag_oy = 0
        self._drag_moved = False
        self.canvas.bind("<Button-1>",         self._click_down)
        self.canvas.bind("<B1-Motion>",        self._drag)
        self.canvas.bind("<ButtonRelease-1>",  self._click_up)
        self.canvas.bind("<Button-3>",         self._right_click)

        self._schedule_idle_talk()
        self._tick()

    # ── render helpers ────────────────────────────────────────────────────────

    def _current_img(self):
        direction = "right" if self.vx >= 0 else "left"
        slot = "side" if self.state == "walking" else "front"
        key  = (self.face, slot, direction)
        if key not in self.cache:
            key = (self.face, "front", direction)
        if key not in self.cache:
            key = next(iter(self.cache))
        return self.cache[key]

    def _set_window_pos(self):
        wx = max(0, round(self.x) - CANVAS_W // 2)
        wy = max(0, round(self.y) - CANVAS_H)
        wx = min(wx, self.sw - CANVAS_W)
        wy = min(wy, self.sh - CANVAS_H)
        self.root.geometry(f"{CANVAS_W}x{CANVAS_H}+{wx}+{wy}")
        self._wx, self._wy = wx, wy

    def _draw(self):
        self.canvas.delete("all")

        if self.state in ("idle", "talking"):
            self.bob_phase += 0.08
            bob = round(2 * math.sin(self.bob_phase))
        else:
            bob = 0

        char_img   = self._current_img()
        char_photo = ImageTk.PhotoImage(char_img)
        self._char_ref = char_photo

        cx = CANVAS_W // 2
        cy = CANVAS_H - 4 + bob
        self.canvas.create_image(cx, cy, anchor="s", image=char_photo)

        if self.bubble_text:
            bub_rgba  = make_bubble(self.bubble_text)
            bub_rgb   = to_rgb(bub_rgba)
            bub_photo = ImageTk.PhotoImage(bub_rgb)
            self._bub_ref = bub_photo
            self.canvas.create_image(cx, cy - TARGET_HEIGHT - 6, anchor="s", image=bub_photo)

    # ── game loop ─────────────────────────────────────────────────────────────

    def _tick(self):
        self.frame_n += 1

        # gravity
        if not self.on_ground:
            self.vy += GRAVITY
            self.y  += self.vy
            floor    = self.sh - 60.0
            if self.y >= floor:
                self.y      = floor
                self.vy     = -abs(self.vy) * BOUNCE
                if abs(self.vy) < 2:
                    self.vy      = 0
                    self.on_ground = True

        # walk
        if self.state == "walking":
            self.x += self.vx
            margin = 100
            if self.x < margin:
                self.x  = margin
                self.vx = abs(self.vx)
                self._say(random.choice(EDGE_LINES), force=True)
            elif self.x > self.sw - margin:
                self.x  = self.sw - margin
                self.vx = -abs(self.vx)
                self._say(random.choice(EDGE_LINES), force=True)

        # state timer
        if self.frame_n % (FPS * 9) == 0:
            self._pick_state()

        # bubble countdown
        if self.bubble_ticks > 0:
            self.bubble_ticks -= 1
            if self.bubble_ticks == 0:
                self.bubble_text = None
                if self.state == "talking":
                    self.state = "idle"

        self._set_window_pos()
        self._draw()
        self.root.after(round(1000 / FPS), self._tick)

    def _pick_state(self):
        if self.bubble_ticks > 0:
            return
        r = random.random()
        if r < 0.5:
            self.state = "walking"
            self.vx    = random.choice([-WALK_SPEED, WALK_SPEED])
        else:
            self.state = "idle"

    # ── dialogue ──────────────────────────────────────────────────────────────

    def _schedule_idle_talk(self):
        delay = random.randint(14000, 38000)
        self.root.after(delay, self._idle_talk)

    def _idle_talk(self):
        pool = [l for l in IDLE_LINES if l != self.last_line]
        self._say(random.choice(pool))
        self._schedule_idle_talk()

    def _say(self, text, force=False):
        if not force and self.bubble_ticks > 0:
            return
        self.bubble_text  = text
        self.last_line    = text
        words             = len(text.split())
        secs              = max(3.5, min(8.0, words * 0.55))
        self.bubble_ticks = round(secs * FPS)
        self.state        = "talking"

    # ── input ─────────────────────────────────────────────────────────────────

    def _click_down(self, e):
        self._drag_ox    = e.x
        self._drag_oy    = e.y
        self._drag_moved = False

    def _drag(self, e):
        dx = e.x - self._drag_ox
        dy = e.y - self._drag_oy
        if abs(dx) > 3 or abs(dy) > 3:
            self._drag_moved = True
        self.x += dx
        self.y += dy
        self._drag_ox   = e.x
        self._drag_oy   = e.y
        self.on_ground  = False
        self.state      = "idle"

    def _click_up(self, e):
        if not self._drag_moved:
            self._poke()
        floor = self.sh - 60.0
        if self.y >= floor:
            self.y         = floor
            self.on_ground = True
        else:
            self.on_ground = False
            self.vy        = 1.0

    def _poke(self):
        pool = [l for l in POKE_LINES if l != self.last_line]
        self._say(random.choice(pool), force=True)
        if self.faces:
            self.face = random.choice(self.faces)
            self.root.after(3500, lambda: setattr(self, "face",
                             self.faces[0] if self.faces else None))

    def _right_click(self, e):
        menu = tk.Menu(self.root, tearoff=0)
        menu.add_command(label="Poke him",     command=self._poke)
        menu.add_separator()
        menu.add_command(label="Quit",         command=self.root.destroy)
        try:
            menu.tk_popup(e.x_root, e.y_root)
        finally:
            menu.grab_release()

    def run(self):
        self.root.mainloop()


if __name__ == "__main__":
    app = XubairApp()
    app.run()
