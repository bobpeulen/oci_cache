import random
import time
import uuid


class Game:
    """Automatic rallies: random returns, first to 11 with a two point lead."""

    def __init__(self, rng=None):
        self.rng = rng or random.Random()
        self.run_id = str(uuid.uuid4())
        self.started_at = time.time()
        self.sequence = 0
        self.match = 1
        self.score = [0, 0]
        self.wins = [0, 0]
        self.total_points = [0, 0]
        self.hits = [0, 0]
        self.rally = 0
        self.longest_rally = 0
        self.last_event = "First serve"
        self.phase = "playing"
        self.pause = 0
        self.serve()

    def serve(self):
        self.x, self.y = 0.5, 0.5
        self.vx = self.rng.choice([-1, 1]) * 0.65
        self.vy = self.rng.uniform(-0.45, 0.45)
        self.paddles = [0.5, 0.5]
        self.rally = 0

    def point(self, winner):
        self.score[winner] += 1
        self.total_points[winner] += 1
        self.last_event = f"Point to {['Ada', 'Linus'][winner]}"
        self.pause = 0.8
        if self.score[winner] >= 11 and abs(self.score[0] - self.score[1]) >= 2:
            self.wins[winner] += 1
            self.last_event = f"{['Ada', 'Linus'][winner]} wins match {self.match}"
            self.phase = "finished"
            self.pause = 3

    def step(self, dt):
        if self.pause > 0:
            self.pause -= dt
            if self.pause <= 0:
                if self.phase == "finished":
                    self.match += 1
                    self.score = [0, 0]
                    self.phase = "playing"
                self.serve()
            return
        self.x += self.vx * dt
        self.y += self.vy * dt
        if self.y < 0.03 or self.y > 0.97:
            self.y = min(0.97, max(0.03, self.y))
            self.vy *= -1
        target = 0 if self.vx < 0 else 1
        self.paddles[target] = min(0.88, max(0.12, self.y))
        if self.x <= 0.05 or self.x >= 0.95:
            self.x = min(0.95, max(0.05, self.x))
            if self.rng.random() < 0.18:
                self.point(1 - target)
            else:
                self.hits[target] += 1
                self.rally += 1
                self.longest_rally = max(self.rally, self.longest_rally)
                self.x = min(0.95, max(0.05, self.x))
                self.vx *= -1.025
                self.vx = max(-1.5, min(1.5, self.vx))
                self.vy = self.rng.uniform(-0.7, 0.7)
                self.last_event = f"{['Ada', 'Linus'][target]} returns · rally {self.rally}"

    def snapshot(self):
        self.sequence += 1
        return dict(schema_version=1, run_id=self.run_id, started_at=self.started_at,
                    sequence=self.sequence, published_at=time.time(), match=self.match,
                    players=["Ada", "Linus"], score=self.score[:], wins=self.wins[:],
                    total_points=self.total_points[:], hits=self.hits[:], rally=self.rally,
                    longest_rally=self.longest_rally, phase=self.phase, last_event=self.last_event,
                    ball=dict(x=self.x, y=self.y), paddles=self.paddles[:])
