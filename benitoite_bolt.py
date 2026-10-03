"""Benitoite Bolt — neon bolt-chain arcade for ElbowOS. Python 3 + pygame.

Slide the charged orb. Fire a bolt through falling storm rings.
Same-hue chains multiply the score. Violet drains leak charge.

  python3 benitoite_bolt.py --play
  python3 benitoite_bolt.py --record
"""
import math
import os
import random
import subprocess
import sys

RECORD = "--record" in sys.argv or os.environ.get("ELBOWOS_RECORD") == "1"
PLAY = "--play" in sys.argv
if RECORD or not PLAY:
    os.environ.setdefault("SDL_VIDEODRIVER", "dummy")
    os.environ.setdefault("SDL_AUDIODRIVER", "dummy")

import pygame

W, H, FPS, SECS = 1080, 1920, 30, 15
OUT = os.environ.get("ELBOWOS_MP4", "/home/workdir/artifacts/BENITOITE_BOLT_ElbowOS.mp4")
TITLE, HANDLE = "BENITOITE BOLT", "x.com/ElbowOS"
WINE, INK = (18, 6, 16), (42, 14, 28)
AMBER, CORAL = (255, 176, 48), (255, 96, 78)
CHART, SAPPH = (196, 255, 72), (88, 156, 255)
WHITE, COPPER = (255, 244, 226), (184, 104, 52)
VIOLET, GOLD = (176, 72, 255), (255, 214, 120)
HUES = (SAPPH, CORAL, CHART)


class Game:
    def __init__(self):
        pygame.init()
        pygame.font.init()
        flags = 0 if PLAY else pygame.HIDDEN
        try:
            self.screen = pygame.display.set_mode((W, H), flags)
        except pygame.error:
            self.screen = pygame.Surface((W, H))
        pygame.display.set_caption(TITLE)
        self.font = pygame.font.SysFont("dejavusans", 64, bold=True)
        self.mid = pygame.font.SysFont("dejavusans", 42, bold=True)
        self.small = pygame.font.SysFont("dejavusans", 32, bold=True)
        self.reset()

    def reset(self):
        self.t = 0
        self.x = W / 2
        self.score = 0
        self.charge = 100
        self.combo = 0
        self.cool = 0
        self.rings = []
        self.bolts = []
        self.sparks = []
        self.pops = []
        self.flash = 0
        self.spawn = 8

    def fire(self):
        if self.cool > 0 or self.charge < 6:
            return
        self.cool = 9
        self.charge = max(0, self.charge - 4)
        hits = [r for r in self.rings if abs(r["x"] - self.x) < 78 and r["y"] < 1460]
        hits.sort(key=lambda r: -r["y"])
        chain, used, col = [], set(), None
        for r in hits:
            if col is None or r["c"] == col:
                col = r["c"]
                chain.append(r)
                used.add(id(r))
                if len(chain) >= 4:
                    break
        pts = 0
        y0, x0 = 1500, self.x
        segs = [(x0, y0)]
        for i, r in enumerate(chain):
            segs.append((r["x"], r["y"]))
            pts += 40 + i * 30
            r["hit"] = 8
            self.sparks.append({"x": r["x"], "y": r["y"], "c": r["c"], "n": 10, "life": 14})
        if chain:
            self.combo = min(9, self.combo + len(chain))
            pts *= self.combo
            self.score += pts
            self.charge = min(100, self.charge + 6 * len(chain))
            self.flash = 6
            self.pops.append({"t": f"+{pts}", "y": chain[0]["y"], "life": 28, "c": col})
        else:
            self.combo = 0
            segs.append((self.x + random.randint(-30, 30), 280))
            self.charge = max(0, self.charge - 8)
        self.bolts.append({"pts": segs, "life": 8, "c": col or GOLD})

    def step(self, keys=None, auto=False):
        self.t += 1
        self.cool = max(0, self.cool - 1)
        self.flash = max(0, self.flash - 1)
        self.spawn -= 1
        if self.spawn <= 0:
            self.spawn = random.randint(10, 18)
            self.rings.append({
                "x": random.randint(160, W - 160),
                "y": 240,
                "vy": random.uniform(6.5, 11.5),
                "c": random.choice(HUES),
                "rot": random.random() * 6,
                "hit": 0,
                "bad": random.random() < 0.14,
            })
        if auto:
            live = [r for r in self.rings if r["y"] < 1400]
            target = min(live, key=lambda r: r["y"]) if live else None
            if target:
                self.x += max(-18, min(18, target["x"] - self.x))
                if abs(self.x - target["x"]) < 36 and self.cool == 0 and self.t % 2 == 0:
                    self.fire()
            else:
                self.x += math.sin(self.t / 11) * 10
        elif keys:
            if keys[pygame.K_LEFT] or keys[pygame.K_a]:
                self.x -= 16
            if keys[pygame.K_RIGHT] or keys[pygame.K_d]:
                self.x += 16
            if keys[pygame.K_SPACE] or keys[pygame.K_UP] or keys[pygame.K_w]:
                self.fire()
        self.x = max(140, min(W - 140, self.x))
        keep = []
        for r in self.rings:
            r["y"] += r["vy"]
            r["rot"] += 0.08
            r["hit"] = max(0, r["hit"] - 1)
            if r["y"] > 1560:
                if r["bad"]:
                    self.score += 15
                else:
                    self.charge = max(0, self.charge - 7)
                    self.combo = 0
                continue
            if r["hit"] == 1:
                continue
            keep.append(r)
        self.rings = [r for r in keep if r["hit"] == 0 or r["hit"] > 1]
        self.rings = [r for r in self.rings if r["hit"] != 1]
        self.bolts = [b for b in self.bolts if b["life"] > 0]
        for b in self.bolts:
            b["life"] -= 1
        for s in self.sparks:
            s["life"] -= 1
        self.sparks = [s for s in self.sparks if s["life"] > 0]
        for p in self.pops:
            p["life"] -= 1
            p["y"] -= 3
        self.pops = [p for p in self.pops if p["life"] > 0]
        if self.charge <= 0 and self.t % 40 == 0:
            self.charge = 28

    def draw(self, surf):
        surf.fill(WINE)
        if self.flash:
            surf.fill((48, 18, 22))
        for i in range(-4, 22):
            x = int((i * 86 + self.t * 3) % (W + 200)) - 100
            pygame.draw.line(surf, (58, 22, 32), (x, 180), (x - 220, H), 2)
        pygame.draw.rect(surf, (28, 10, 22), (0, 0, W, 200))
        for i in range(6):
            cx = 120 + i * 170 + int(math.sin(self.t / 9 + i) * 12)
            pygame.draw.ellipse(surf, (48, 16, 36), (cx, 40, 150, 70))
            if (self.t + i * 5) % 17 < 3:
                pygame.draw.line(surf, GOLD, (cx + 70, 90), (cx + 40, 180), 3)
        pygame.draw.rect(surf, COPPER, (70, 220, 18, 1280), border_radius=8)
        pygame.draw.rect(surf, COPPER, (W - 88, 220, 18, 1280), border_radius=8)
        pygame.draw.rect(surf, (62, 24, 36), (110, 1460, W - 220, 28), border_radius=12)
        pygame.draw.rect(surf, AMBER, (110, 1460, int((W - 220) * self.charge / 100), 28), border_radius=12)
        for r in self.rings:
            col = VIOLET if r["bad"] else r["c"]
            rad = 46 + (6 if r["hit"] else 0)
            pygame.draw.circle(surf, col, (int(r["x"]), int(r["y"])), rad, 8)
            pygame.draw.circle(surf, WHITE, (int(r["x"]), int(r["y"])), 16, 3)
            ang = r["rot"]
            pygame.draw.line(surf, col, (r["x"], r["y"]), (r["x"] + math.cos(ang) * 34, r["y"] + math.sin(ang) * 34), 4)
        for b in self.bolts:
            if len(b["pts"]) > 1:
                jagged = []
                for (x, y) in b["pts"]:
                    jagged.append((x + random.randint(-8, 8), y))
                pygame.draw.lines(surf, WHITE, False, jagged, 10)
                pygame.draw.lines(surf, b["c"], False, jagged, 4)
        for s in self.sparks:
            for k in range(s["n"]):
                ang = k * 0.7 + self.t
                d = (16 - s["life"]) * 5
                pygame.draw.circle(surf, s["c"], (int(s["x"] + math.cos(ang) * d), int(s["y"] + math.sin(ang) * d)), 5)
        px, py = int(self.x), 1500
        pygame.draw.circle(surf, (80, 40, 16), (px, py), 54)
        pygame.draw.circle(surf, AMBER, (px, py), 40)
        pygame.draw.circle(surf, WHITE, (px, py), 16)
        pygame.draw.circle(surf, GOLD, (px, py), 58, 3)
        title = self.font.render(TITLE, True, AMBER)
        surf.blit(title, (W // 2 - title.get_width() // 2, 48))
        sc = self.mid.render(f"SCORE  {self.score}", True, WHITE)
        surf.blit(sc, (W // 2 - sc.get_width() // 2, 128))
        handle = self.small.render(HANDLE, True, GOLD)
        surf.blit(handle, (W // 2 - handle.get_width() // 2, 1760))
        tag = self.small.render(f"CHAIN x{max(1, self.combo)}", True, CHART)
        surf.blit(tag, (120, 1380))
        for p in self.pops:
            lab = self.mid.render(p["t"], True, p["c"])
            surf.blit(lab, (W // 2 - lab.get_width() // 2, int(p["y"])))


def record():
    g = Game()
    os.makedirs(os.path.dirname(OUT), exist_ok=True)
    cmd = [
        "ffmpeg", "-y", "-f", "rawvideo", "-pix_fmt", "rgb24",
        "-s", f"{W}x{H}", "-r", str(FPS), "-i", "-",
        "-an", "-c:v", "libx264", "-pix_fmt", "yuv420p",
        "-crf", "20", "-preset", "veryfast", "-movflags", "+faststart", OUT,
    ]
    proc = subprocess.Popen(cmd, stdin=subprocess.PIPE, stderr=subprocess.PIPE)
    frames = FPS * SECS
    try:
        for _ in range(frames):
            g.step(auto=True)
            g.draw(g.screen)
            proc.stdin.write(pygame.image.tobytes(g.screen, "RGB"))
    finally:
        proc.stdin.close()
    err = proc.stderr.read().decode("utf-8", "replace")
    code = proc.wait()
    if code != 0:
        sys.stderr.write(err[-2000:])
        raise SystemExit(f"ffmpeg failed: {code}")
    alt = "/workspace/artifacts/BENITOITE_BOLT_ElbowOS.mp4"
    if os.path.abspath(OUT) != os.path.abspath(alt):
        os.makedirs(os.path.dirname(alt), exist_ok=True)
        with open(OUT, "rb") as src, open(alt, "wb") as dst:
            dst.write(src.read())
    print(OUT)


def play():
    g = Game()
    clock = pygame.time.Clock()
    while True:
        for e in pygame.event.get():
            if e.type == pygame.QUIT:
                return
            if e.type == pygame.KEYDOWN and e.key == pygame.K_r:
                g.reset()
        g.step(keys=pygame.key.get_pressed())
        g.draw(g.screen)
        pygame.display.flip()
        clock.tick(FPS)


if __name__ == "__main__":
    if PLAY:
        play()
    else:
        record()
