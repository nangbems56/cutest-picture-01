#!/usr/bin/env python3
"""Mochi the Moon Bunny - a picture for make.fun's "Make the cutest picture".

A chubby cream bunny with huge glossy eyes, blush cheeks and a tiny carrot,
drawn entirely in code: supersampled vector shapes (ellipses, polygons,
stamped curves) in pure Python standard library, soft pastel palette, gentle
vignette. Deterministic: the same bytes every run.

Run:  python3 main.py        (writes /output/entry.png, or ./entry.png)
"""

import math
import os
import random
import struct
import zlib

SS = 2                      # supersampling factor
W = 1024 * SS               # working resolution
H = 1024 * SS
OUT = 1024
SEED = 20261113


def S(v):
    """Scale a 1024-space measurement into working pixels."""
    return v * SS


# --------------------------------------------------------------- canvas ----

class Canvas:
    def __init__(self, w, h):
        self.w = w
        self.h = h
        self.r = [0.0] * (w * h)
        self.g = [0.0] * (w * h)
        self.b = [0.0] * (w * h)

    def blend(self, idx, color, alpha):
        if alpha <= 0.0:
            return
        ia = 1.0 - alpha
        self.r[idx] = self.r[idx] * ia + color[0] * alpha
        self.g[idx] = self.g[idx] * ia + color[1] * alpha
        self.b[idx] = self.b[idx] * ia + color[2] * alpha

    def ellipse(self, cx, cy, rx, ry, color, alpha=1.0, rot=0.0):
        cosr = math.cos(rot)
        sinr = math.sin(rot)
        x0 = max(0, int(cx - rx - 2))
        x1 = min(self.w - 1, int(cx + rx + 2))
        y0 = max(0, int(cy - ry - 2))
        y1 = min(self.h - 1, int(cy + ry + 2))
        for y in range(y0, y1 + 1):
            base = y * self.w
            dy = y + 0.5 - cy
            for x in range(x0, x1 + 1):
                dx = x + 0.5 - cx
                lx = dx * cosr + dy * sinr
                ly = -dx * sinr + dy * cosr
                d = (lx / rx) ** 2 + (ly / ry) ** 2
                if d < 1.0:
                    edge = min(1.0, (1.0 - d) * rx * 0.5)
                    self.blend(base + x, color, alpha * min(1.0, edge))

    def circle(self, cx, cy, r, color, alpha=1.0):
        self.ellipse(cx, cy, r, r, color, alpha)

    def polygon(self, pts, color, alpha=1.0):
        xs = [p[0] for p in pts]
        ys = [p[1] for p in pts]
        x0 = max(0, int(min(xs)) - 1)
        x1 = min(self.w - 1, int(max(xs)) + 1)
        y0 = max(0, int(min(ys)) - 1)
        y1 = min(self.h - 1, int(max(ys)) + 1)
        n = len(pts)
        for y in range(y0, y1 + 1):
            base = y * self.w
            py = y + 0.5
            for x in range(x0, x1 + 1):
                px = x + 0.5
                inside = False
                j = n - 1
                for i in range(n):
                    xi, yi = pts[i]
                    xj, yj = pts[j]
                    if (yi > py) != (yj > py):
                        xint = (xj - xi) * (py - yi) / (yj - yi) + xi
                        if px < xint:
                            inside = not inside
                    j = i
                if inside:
                    self.blend(base + x, color, alpha)

    def stamp_curve(self, pts, radius, color, alpha=1.0):
        for (x, y) in pts:
            self.circle(x, y, radius, color, alpha)


# -------------------------------------------------------------- palette ----

def hx(s):
    return tuple(int(s[i:i + 2], 16) / 255.0 for i in (0, 2, 4))


CREAM = hx("fff9f1")
CREAM_SHADE = hx("f7e3cf")
OUTLINE = hx("8a5a44")
PINK = hx("ffb7c9")
PINK_DEEP = hx("ff8fab")
BLUSH = hx("ff9db4")
EYE = hx("4a2c2a")
NOSE = hx("f97d9c")
GOLD = hx("ffc93c")
CARROT = hx("ff9f43")
LEAF = hx("7bc96f")
WHITE = (1.0, 1.0, 1.0)


# -------------------------------------------------------------- drawing ----

def background(cv, rng):
    top = hx("ffe3ef")
    mid = hx("ffdfd2")
    bot = hx("ffd3a8")
    for y in range(H):
        t = y / H
        if t < 0.55:
            a, b, f = top, mid, t / 0.55
        else:
            a, b, f = mid, bot, (t - 0.55) / 0.45
        row = tuple(a[i] + (b[i] - a[i]) * f for i in range(3))
        base = y * W
        for x in range(W):
            dx = (x - W / 2) / W
            dy = (y - H * 0.42) / H
            halo = max(0.0, 1.0 - (dx * dx + dy * dy) * 3.4)
            idx = base + x
            cv.r[idx] = row[0] + halo * 0.10
            cv.g[idx] = row[1] + halo * 0.09
            cv.b[idx] = row[2] + halo * 0.06
    # Soft polka dots.
    for _ in range(90):
        cv.circle(rng.uniform(0, W), rng.uniform(0, H),
                  S(rng.uniform(4, 11)), WHITE, alpha=0.16)


def heart(cv, cx, cy, size, color, alpha, rot=0.0):
    pts = []
    for deg in range(0, 360, 6):
        t = math.radians(deg)
        x = 16 * math.sin(t) ** 3
        y = (13 * math.cos(t) - 5 * math.cos(2 * t)
             - 2 * math.cos(3 * t) - math.cos(4 * t))
        xr = x * math.cos(rot) - (-y) * math.sin(rot)
        yr = x * math.sin(rot) + (-y) * math.cos(rot)
        pts.append((cx + xr * size, cy + yr * size))
    cv.polygon(pts, color, alpha)


def star4(cv, cx, cy, r, color, alpha):
    pts = [(cx, cy - r), (cx + r * 0.22, cy - r * 0.22), (cx + r, cy),
           (cx + r * 0.22, cy + r * 0.22), (cx, cy + r),
           (cx - r * 0.22, cy + r * 0.22), (cx - r, cy),
           (cx - r * 0.22, cy - r * 0.22)]
    cv.polygon(pts, color, alpha)


def star5(cv, cx, cy, r, color, rot=-math.pi / 2):
    pts = []
    for i in range(10):
        rad = r if i % 2 == 0 else r * 0.46
        a = rot + i * math.pi / 5
        pts.append((cx + rad * math.cos(a), cy + rad * math.sin(a)))
    cv.polygon(pts, color, 1.0)


def outlined_ellipse(cv, cx, cy, rx, ry, fill, rot=0.0, width=7, alpha=1.0):
    cv.ellipse(cx, cy, rx, ry, OUTLINE, alpha, rot)
    cv.ellipse(cx, cy, rx - S(width), ry - S(width), fill, alpha, rot)


def bunny(cv):
    cx = S(512)
    # Ground shadow.
    cv.ellipse(cx, S(880), S(300), S(52), hx("e8a87c"), alpha=0.35)
    # Ears (behind head): left straight up, right with a gentle flop.
    outlined_ellipse(cv, S(392), S(238), S(62), S(168), CREAM, rot=-0.16)
    cv.ellipse(S(392), S(238), S(30), S(120), PINK, 0.95, rot=-0.16)
    outlined_ellipse(cv, S(622), S(215), S(62), S(160), CREAM, rot=0.38)
    cv.ellipse(S(622), S(215), S(30), S(112), PINK, 0.95, rot=0.38)
    # Body: a squashed chubby oval.
    outlined_ellipse(cv, cx, S(795), S(215), S(150), CREAM)
    cv.ellipse(cx, S(815), S(120), S(95), WHITE, 0.55)
    # Feet with toe beans.
    for fx in (S(392), S(632)):
        outlined_ellipse(cv, fx, S(918), S(72), S(40), CREAM)
        cv.ellipse(fx, S(912), S(20), S(14), PINK_DEEP, 0.9)
        for toe in (-1, 1):
            cv.circle(fx + toe * S(30), S(928), S(8), PINK_DEEP, 0.9)
    # Head: one big round circle.
    outlined_ellipse(cv, cx, S(520), S(272), S(252), CREAM)
    # Hair tuft: three little bumps on top.
    for (tx, ty, tr) in ((468, 268, 34), (516, 248, 40), (562, 268, 32)):
        cv.circle(S(tx), S(ty), S(tr), CREAM)
        cv.circle(S(tx), S(ty), S(tr), OUTLINE, 0.0)
    # Star hairpin by the right ear.
    star5(cv, S(700), S(330), S(34), GOLD, rot=-0.4)
    star5(cv, S(700), S(330), S(34), OUTLINE, rot=-0.4)
    star5(cv, S(700), S(330), S(26), GOLD, rot=-0.4)
    # Blush cheeks.
    cv.ellipse(S(330), S(600), S(56), S(30), BLUSH, 0.75, rot=-0.15)
    cv.ellipse(S(694), S(600), S(56), S(30), BLUSH, 0.75, rot=0.15)
    # Eyes: big, glossy, slightly oval.
    for ex in (S(408), S(616)):
        cv.ellipse(ex, S(520), S(37), S(55), EYE)
        cv.circle(ex - S(13), S(498), S(15), WHITE, 0.98)
        cv.circle(ex + S(12), S(545), S(7), WHITE, 0.9)
    # Nose + tiny mouth.
    cv.ellipse(cx, S(572), S(15), S(10), NOSE)
    mouth = []
    for t in range(0, 21):
        f = t / 20
        a = math.pi * (0.15 + 0.7 * f)
        mouth.append((cx - S(17) + S(17) * math.cos(a) * -1,
                      S(584) + S(13) * math.sin(a)))
    cv.stamp_curve(mouth, S(4.5), OUTLINE)
    mouth2 = [(2 * cx - x, y) for (x, y) in mouth]
    cv.stamp_curve(mouth2, S(4.5), OUTLINE)
    # The carrot, hugged at the belly.
    cv.ellipse(S(512), S(800), S(34), S(62), OUTLINE, 1.0, rot=0.5)
    cv.ellipse(S(512), S(800), S(27), S(55), CARROT, 1.0, rot=0.5)
    for (lx, ly, lr) in ((486, 736, 0.9), (512, 724, 0.2), (538, 736, -0.7)):
        cv.ellipse(S(lx), S(ly), S(11), S(30), LEAF, 1.0, rot=lr)
    # Paws over the carrot.
    outlined_ellipse(cv, S(428), S(772), S(46), S(30), CREAM, rot=-0.5, width=6)
    outlined_ellipse(cv, S(596), S(772), S(46), S(30), CREAM, rot=0.5, width=6)


def deco(cv, rng):
    for (x, y, s, a, r) in ((150, 190, 15, 0.85, -0.2), (880, 150, 12, 0.8, 0.25),
                            (905, 420, 10, 0.65, 0.1), (120, 470, 10, 0.6, -0.3),
                            (205, 760, 9, 0.55, 0.2), (835, 720, 9, 0.55, -0.15)):
        heart(cv, S(x), S(y), S(s) / 16, PINK_DEEP, a, rot=r)
    for (x, y, s, a) in ((240, 120, 17, 0.95), (790, 260, 13, 0.9),
                         (140, 620, 12, 0.85), (890, 580, 15, 0.9),
                         (330, 90, 11, 0.8), (690, 110, 10, 0.75)):
        star4(cv, S(x), S(y), S(s), GOLD, a)
        star4(cv, S(x), S(y), S(s) * 0.55, WHITE, a * 0.7)


# -------------------------------------------------------------- output -----

def downscale(canvas):
    rows = []
    for y in range(OUT):
        row = bytearray(OUT * 3)
        for x in range(OUT):
            acc = [0.0, 0.0, 0.0]
            for dy in range(SS):
                base = (y * SS + dy) * W + x * SS
                for dx in range(SS):
                    idx = base + dx
                    acc[0] += canvas.r[idx]
                    acc[1] += canvas.g[idx]
                    acc[2] += canvas.b[idx]
            n = SS * SS
            o = x * 3
            # Soft vignette toward the corners.
            vx = (x - OUT / 2) / OUT
            vy = (y - OUT / 2) / OUT
            vig = 1.0 - 0.10 * (vx * vx + vy * vy) * 2
            for ch in range(3):
                v = min(1.0, acc[ch] / n) * vig
                row[o + ch] = 255 if v >= 1.0 else int(v * 256)
        rows.append(bytes(row))
    return rows


def encode_png(rows, w, h):
    raw = b"".join(b"\x00" + r for r in rows)

    def chunk(tag, data):
        c = struct.pack(">I", len(data)) + tag + data
        return c + struct.pack(">I", zlib.crc32(tag + data) & 0xFFFFFFFF)

    ihdr = struct.pack(">IIBBBBB", w, h, 8, 2, 0, 0, 0)
    return (b"\x89PNG\r\n\x1a\n" + chunk(b"IHDR", ihdr)
            + chunk(b"IDAT", zlib.compress(raw, 9)) + chunk(b"IEND", b""))


def render():
    rng = random.Random(SEED)
    cv = Canvas(W, H)
    background(cv, rng)
    bunny(cv)
    deco(cv, rng)
    return encode_png(downscale(cv), OUT, OUT)


def main():
    png = render()
    out = "/output/entry.png"
    try:
        os.makedirs("/output", exist_ok=True)
    except OSError:
        out = "entry.png"
    if not os.path.isdir("/output"):
        out = "entry.png"
    with open(out, "wb") as f:
        f.write(png)
    print(f"wrote {out} ({len(png)} bytes)")


if __name__ == "__main__":
    main()
