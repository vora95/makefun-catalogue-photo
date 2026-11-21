#!/usr/bin/env python3
"""The Catalogue Photo of an Impossible Gadget.

A pure-stdlib program that paints a studio catalogue photograph of the
LEVITEA anti-gravity teapot: a brushed-steel teapot whose spout pours a
stream of tea UPWARD into a porcelain cup floating in mid-air above it.
The cup is the single accessory. No network, no randomness (fully
deterministic), writes /output/entry.png (1024x1024 PNG, < 1 MiB).
"""
import math
import os
import struct
import zlib
from pathlib import Path

W = H = 1024


# ---------------------------------------------------------------- canvas
class Canvas:
    def __init__(self):
        self.px = bytearray(W * H * 3)

    def blend(self, x, y, r, g, b, a):
        if a <= 0.0 or x < 0 or y < 0 or x >= W or y >= H:
            return
        if a > 1.0:
            a = 1.0
        i = (y * W + x) * 3
        px = self.px
        px[i] = int(px[i] * (1 - a) + r * a)
        px[i + 1] = int(px[i + 1] * (1 - a) + g * a)
        px[i + 2] = int(px[i + 2] * (1 - a) + b * a)

    def set(self, x, y, r, g, b):
        if 0 <= x < W and 0 <= y < H:
            i = (y * W + x) * 3
            self.px[i] = r
            self.px[i + 1] = g
            self.px[i + 2] = b

    def vgrad(self, top, bottom):
        for y in range(H):
            t = y / (H - 1)
            r = int(top[0] + (bottom[0] - top[0]) * t)
            g = int(top[1] + (bottom[1] - top[1]) * t)
            b = int(top[2] + (bottom[2] - top[2]) * t)
            base = y * W * 3
            for x in range(W):
                i = base + x * 3
                self.px[i] = r
                self.px[i + 1] = g
                self.px[i + 2] = b

    def radial_light(self, cx, cy, radius, amount):
        """Gentle brightening towards (cx, cy), like a softbox."""
        x0 = max(0, int(cx - radius))
        x1 = min(W, int(cx + radius))
        y0 = max(0, int(cy - radius))
        y1 = min(H, int(cy + radius))
        for y in range(y0, y1):
            dy = (y - cy) / radius
            for x in range(x0, x1):
                dx = (x - cx) / radius
                d = dx * dx + dy * dy
                if d >= 1.0:
                    continue
                a = amount * (1.0 - d)
                i = (y * W + x) * 3
                px = self.px
                px[i] = min(255, int(px[i] + (255 - px[i]) * a))
                px[i + 1] = min(255, int(px[i + 1] + (255 - px[i + 1]) * a))
                px[i + 2] = min(255, int(px[i + 2] + (255 - px[i + 2]) * a))

    def soft_ellipse(self, cx, cy, rx, ry, color, alpha_max):
        """Blurred shadow ellipse with smooth falloff."""
        x0 = max(0, int(cx - rx))
        x1 = min(W, int(cx + rx) + 1)
        y0 = max(0, int(cy - ry))
        y1 = min(H, int(cy + ry) + 1)
        for y in range(y0, y1):
            dy = (y - cy) / ry
            for x in range(x0, x1):
                dx = (x - cx) / rx
                d = dx * dx + dy * dy
                if d >= 1.0:
                    continue
                a = alpha_max * (1.0 - d) * (1.0 - d)
                self.blend(x, y, color[0], color[1], color[2], a)

    def disc(self, cx, cy, r, color, alpha=1.0):
        x0 = max(0, int(cx - r) - 1)
        x1 = min(W, int(cx + r) + 2)
        y0 = max(0, int(cy - r) - 1)
        y1 = min(H, int(cy + r) + 2)
        for y in range(y0, y1):
            for x in range(x0, x1):
                dx = x - cx
                dy = y - cy
                d = math.sqrt(dx * dx + dy * dy)
                if d <= r - 0.7:
                    self.blend(x, y, color[0], color[1], color[2], alpha)
                elif d <= r + 0.7:
                    self.blend(x, y, color[0], color[1], color[2],
                               alpha * (r + 0.7 - d) / 1.4)

    def ellipse(self, cx, cy, rx, ry, color, alpha=1.0):
        x0 = max(0, int(cx - rx) - 1)
        x1 = min(W, int(cx + rx) + 2)
        y0 = max(0, int(cy - ry) - 1)
        y1 = min(H, int(cy + ry) + 2)
        for y in range(y0, y1):
            dy = (y - cy) / ry
            for x in range(x0, x1):
                dx = (x - cx) / rx
                d = dx * dx + dy * dy
                if d <= 1.0:
                    edge = 1.0
                    if d > 0.92:
                        edge = (1.0 - d) / 0.08
                    self.blend(x, y, color[0], color[1], color[2],
                               alpha * edge)

    def poly(self, pts, color, alpha=1.0):
        """Scanline fill of a polygon (list of (x, y))."""
        ys = [p[1] for p in pts]
        y0 = max(0, int(min(ys)))
        y1 = min(H - 1, int(max(ys)) + 1)
        n = len(pts)
        for y in range(y0, y1 + 1):
            xs = []
            for i in range(n):
                x1, y1p = pts[i]
                x2, y2p = pts[(i + 1) % n]
                if (y1p <= y < y2p) or (y2p <= y < y1p):
                    t = (y - y1p) / (y2p - y1p)
                    xs.append(x1 + t * (x2 - x1))
            xs.sort()
            for k in range(0, len(xs) - 1, 2):
                xa = max(0, int(xs[k]))
                xb = min(W - 1, int(xs[k + 1]))
                for x in range(xa, xb + 1):
                    self.blend(x, y, color[0], color[1], color[2], alpha)

    def thick_polyline(self, pts, widths, color, alpha=1.0):
        """Stroke a polyline with round joins/caps; widths per point."""
        # dense resample
        dense = []
        for i in range(len(pts) - 1):
            x1, y1 = pts[i]
            x2, y2 = pts[i + 1]
            w1 = widths[i]
            w2 = widths[i + 1]
            seg = max(2, int(math.hypot(x2 - x1, y2 - y1) / 3))
            for s in range(seg):
                t = s / seg
                dense.append((x1 + (x2 - x1) * t, y1 + (y2 - y1) * t,
                              w1 + (w2 - w1) * t))
        dense.append((pts[-1][0], pts[-1][1], widths[-1]))
        for (x, y, w) in dense:
            r = w / 2.0
            self.disc(x, y, r, color, alpha)


# ------------------------------------------------------------ tiny font
FONT = {
    'A': ("01110", "10001", "10001", "11111", "10001", "10001", "10001"),
    'D': ("11110", "10001", "10001", "10001", "10001", "10001", "11110"),
    'E': ("11111", "10000", "10000", "11110", "10000", "10000", "11111"),
    'G': ("01110", "10001", "10000", "10111", "10001", "10001", "01110"),
    'I': ("11111", "00100", "00100", "00100", "00100", "00100", "11111"),
    'L': ("10000", "10000", "10000", "10000", "10000", "10000", "11111"),
    'M': ("10001", "11011", "10101", "10101", "10001", "10001", "10001"),
    'O': ("01110", "10001", "10001", "10001", "10001", "10001", "01110"),
    'T': ("11111", "00100", "00100", "00100", "00100", "00100", "00100"),
    'V': ("10001", "10001", "10001", "10001", "10001", "01010", "00100"),
    '1': ("00100", "01100", "00100", "00100", "00100", "00100", "01110"),
    '-': ("00000", "00000", "00000", "11111", "00000", "00000", "00000"),
    '.': ("00000", "00000", "00000", "00000", "00000", "01100", "01100"),
    ' ': ("00000", "00000", "00000", "00000", "00000", "00000", "00000"),
}


def draw_text(cv, x, y, text, scale, color, alpha=1.0):
    cx = x
    for ch in text:
        glyph = FONT.get(ch, FONT[' '])
        for row in range(7):
            bits = glyph[row]
            for col in range(5):
                if bits[col] == '1':
                    for dy in range(scale):
                        for dx in range(scale):
                            cv.blend(cx + col * scale + dx,
                                     y + row * scale + dy,
                                     color[0], color[1], color[2], alpha)
        cx += 6 * scale


def text_w(text, scale):
    return len(text) * 6 * scale - scale


# ------------------------------------------------------------- helpers
def lerp(a, b, t):
    return a + (b - a) * t


def steel_shade(t):
    """Brushed steel: bright left, dark right, with a soft highlight band."""
    # t in [0,1] across the body, 0 = left edge
    base = lerp(96, 226, t)
    band = 46 * math.exp(-((t - 0.30) ** 2) / 0.012)
    edge = 26 * math.exp(-((t - 0.97) ** 2) / 0.004)
    v = base + band - edge
    v = max(58, min(238, v))
    return (int(v), int(v * 1.005), int(min(255, v * 1.03)))


def bez(p0, p1, p2, p3, n=40):
    pts = []
    for i in range(n + 1):
        t = i / n
        mt = 1 - t
        x = (mt ** 3 * p0[0] + 3 * mt * mt * t * p1[0] +
             3 * mt * t * t * p2[0] + t ** 3 * p3[0])
        y = (mt ** 3 * p0[1] + 3 * mt * mt * t * p1[1] +
             3 * mt * t * t * p2[1] + t ** 3 * p3[1])
        pts.append((x, y))
    return pts


# ---------------------------------------------------------------- paint
def paint():
    cv = Canvas()
    # Seamless studio paper: warm light grey, brighter near the key light.
    cv.vgrad((236, 234, 230), (203, 200, 195))
    cv.radial_light(360, 300, 700, 0.10)

    # --- contact shadow under the teapot (grounds the hero) ---
    cv.soft_ellipse(470, 812, 265, 34, (58, 53, 48), 0.42)
    # --- soft shadow of the floating cup on the backdrop ---
    cv.soft_ellipse(600, 296, 120, 22, (90, 86, 80), 0.14)

    # --- teapot body: superellipse, brushed steel ---
    cx, cy, a, b, n = 470, 612, 212, 186, 3.1
    x0 = int(cx - a)
    x1 = int(cx + a)
    y0 = int(cy - b)
    y1 = int(cy + b)
    for y in range(y0, y1 + 1):
        dy = abs((y - cy) / b)
        if dy >= 1.0:
            continue
        half = a * (1.0 - dy ** n) ** (1.0 / n)
        for x in range(int(cx - half), int(cx + half) + 1):
            t = (x - (cx - a)) / (2 * a)
            # vertical shading: slightly darker towards the base
            vshade = 1.0 - 0.10 * max(0.0, (y - cy) / b)
            # fine brushed streaks, deterministic
            streak = 5 * math.sin(x * 1.9 + 2.0 * math.sin(y * 0.05))
            r, g, bl = steel_shade(t)
            r = max(40, min(245, int(r * vshade + streak)))
            g = max(40, min(245, int(g * vshade + streak)))
            bl = max(40, min(250, int(bl * vshade + streak)))
            # anti-aliased rim
            edge = min(1.0, (half - abs(x - cx)) / 1.5 + 0.15)
            cv.blend(x, y, r, g, bl, min(1.0, edge))

    # base foot ring
    cv.ellipse(470, 792, 150, 16, (96, 100, 108), 0.85)
    cv.ellipse(470, 788, 150, 14, (150, 154, 162), 0.9)

    # --- lid: dome + knob ---
    cv.ellipse(470, 436, 152, 40, (196, 200, 208), 1.0)
    cv.ellipse(470, 430, 152, 34, steel_shade(0.42), 1.0)
    cv.ellipse(430, 420, 70, 12, (226, 230, 236), 0.55)
    cv.disc(470, 398, 26, (150, 155, 164), 1.0)
    cv.disc(464, 392, 12, (215, 219, 226), 0.9)
    cv.disc(470, 398, 26, (0, 0, 0), 0.0)  # no-op keeps shape explicit

    # --- spout: sweeping up to the left, tip pointing at the sky ---
    spout = bez((318, 590), (252, 520), (238, 440), (284, 372), 36)
    widths = [58 - 24 * (i / (len(spout) - 1)) for i in range(len(spout))]
    for i, (x, y) in enumerate(spout):
        t = (x - 200) / 160.0
        col = steel_shade(max(0.0, min(1.0, t)))
        cv.disc(x, y, widths[i] / 2.0, col, 1.0)
    # spout highlight
    hi = bez((306, 566), (262, 500), (254, 436), (282, 386), 30)
    cv.thick_polyline(hi, [7] * len(hi), (238, 241, 245), 0.55)
    # spout mouth (dark opening, tilted up)
    cv.ellipse(286, 370, 20, 11, (52, 48, 44), 1.0)
    cv.ellipse(286, 368, 14, 7, (26, 22, 20), 1.0)

    # --- handle: bold C on the right, dark edge so it reads on paper ---
    handle = bez((652, 528), (762, 560), (772, 660), (656, 700), 36)
    for i, (x, y) in enumerate(handle):
        cv.disc(x, y, 20, (118, 122, 130), 1.0)
    for i, (x, y) in enumerate(handle):
        t = 0.55 + 0.35 * (i / (len(handle) - 1))
        col = steel_shade(max(0.0, min(1.0, t)))
        cv.disc(x, y, 17, col, 1.0)
    cv.thick_polyline(bez((668, 548), (736, 576), (744, 648), (668, 682), 24),
                      [5] * 25, (238, 241, 245), 0.5)

    # --- brand plate on the body (text belongs to the product) ---
    px0, py0, pw, ph = 392, 596, 156, 52
    cv.poly([(px0 + 8, py0), (px0 + pw - 8, py0), (px0 + pw, py0 + 8),
             (px0 + pw, py0 + ph - 8), (px0 + pw - 8, py0 + ph),
             (px0 + 8, py0 + ph), (px0, py0 + ph - 8), (px0, py0 + 8)],
            (48, 52, 58), 0.92)
    label = "LEVITEA"
    draw_text(cv, px0 + (pw - text_w(label, 2)) // 2, py0 + 8,
              label, 2, (232, 234, 238), 0.95)
    sub = "MODEL AG-1"
    draw_text(cv, px0 + (pw - text_w(sub, 1)) // 2, py0 + 34,
              sub, 1, (168, 172, 180), 0.95)

    # --- the impossible pour: tea rises from the spout into the cup ---
    stream = bez((286, 362), (330, 268), (430, 216), (540, 208), 40)
    sw = [15 - 6 * (i / (len(stream) - 1)) for i in range(len(stream))]
    for i, (x, y) in enumerate(stream):
        t = i / (len(stream) - 1)
        col = (int(lerp(150, 214, t)), int(lerp(88, 150, t)),
               int(lerp(16, 52, t)))
        cv.disc(x, y, sw[i] / 2.0, col, 1.0)
    # bright core of the stream
    core = bez((288, 360), (332, 272), (428, 220), (536, 210), 36)
    cv.thick_polyline(core, [4] * len(core), (246, 198, 110), 0.75)
    # droplets escaping upward: the pour defies gravity
    for (dx, dy, dr) in [(318, 318, 6), (352, 272, 5), (398, 232, 6),
                         (452, 210, 4), (500, 196, 5)]:
        cv.disc(dx, dy, dr, (214, 150, 52), 1.0)
        cv.disc(dx - 1, dy - 1, max(1, dr - 3), (246, 200, 110), 0.9)

    # --- the floating cup: the one accessory, hovering, tea inside ---
    # tilt the cup slightly by drawing it sheared: rim ellipse + body
    cv.ellipse(560, 148, 96, 26, (250, 250, 248), 1.0)          # rim outer
    cv.ellipse(560, 148, 84, 20, (196, 120, 40), 1.0)           # tea surface
    cv.ellipse(560, 147, 84, 20, (226, 168, 84), 0.55)          # tea light
    # cup body: trapezoid with curved sides
    cv.poly([(470, 150), (650, 150), (626, 216), (494, 216)],
            (244, 244, 242), 1.0)
    cv.poly([(470, 150), (500, 150), (494, 216), (486, 216)],
            (210, 210, 206), 1.0)                                # left shade
    cv.poly([(622, 150), (650, 150), (634, 216), (626, 216)],
            (226, 226, 222), 1.0)                                # right light
    cv.ellipse(560, 216, 66, 12, (228, 228, 224), 1.0)          # base
    # cup handle
    cup_h = bez((648, 158), (690, 164), (690, 196), (644, 200), 20)
    cv.thick_polyline(cup_h, [9] * len(cup_h), (244, 244, 242), 1.0)
    # steam curling up from the floating cup
    for sx, phase in [(528, 0.0), (560, 1.4), (592, 2.6)]:
        pts = [(sx + 10 * math.sin((y - 60) / 26.0 + phase), y)
               for y in range(58, 132, 4)]
        cv.thick_polyline(pts, [7] * len(pts), (255, 255, 255), 0.16)

    # --- gentle vignette so the hero pops like a catalogue cover ---
    # Only the corner bands can exceed the threshold; skip the middle.
    for y in range(H):
        dy = (y - H / 2) / (H / 2)
        rest = 0.86 - dy * dy
        if rest <= 0.0:
            xs = range(W)
            for x in xs:
                dx = (x - W / 2) / (W / 2)
                d = dx * dx + dy * dy
                a = min(0.10, (d - 0.86) * 0.35)
                cv.blend(x, y, 70, 66, 60, a)
            continue
        dx_lim = math.sqrt(rest)
        x_edge = int(dx_lim * (W / 2))
        for x in list(range(0, W // 2 - x_edge)) + list(range(W // 2 + x_edge, W)):
            dx = (x - W / 2) / (W / 2)
            d = dx * dx + dy * dy
            if d > 0.86:
                a = min(0.10, (d - 0.86) * 0.35)
                cv.blend(x, y, 70, 66, 60, a)
    return cv


# ------------------------------------------------------------------ png
def write_png(cv, path):
    raw = bytearray()
    stride = W * 3
    for y in range(H):
        raw.append(0)  # filter None
        raw += cv.px[y * stride:(y + 1) * stride]
    data = zlib.compress(bytes(raw), 6)
    png = bytearray(b"\x89PNG\r\n\x1a\n")

    def chunk(tag, payload):
        png.extend(struct.pack(">I", len(payload)))
        png.extend(tag)
        png.extend(payload)
        png.extend(struct.pack(">I", zlib.crc32(tag + payload) & 0xFFFFFFFF))

    chunk(b"IHDR", struct.pack(">IIBBBBB", W, H, 8, 2, 0, 0, 0))
    chunk(b"IDAT", data)
    chunk(b"IEND", b"")
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_bytes(bytes(png))
    return len(png)


def main():
    out = Path("/output/entry.png")
    try:
        out.parent.mkdir(parents=True, exist_ok=True)
        probe = out.parent / ".write-test"
        probe.write_bytes(b"")
        probe.unlink()
    except OSError:
        out = Path(__file__).resolve().parent / "output" / "entry.png"
    cv = paint()
    size = write_png(cv, out)
    print(f"wrote {out} {size} bytes ({W}x{H})")


if __name__ == "__main__":
    main()
