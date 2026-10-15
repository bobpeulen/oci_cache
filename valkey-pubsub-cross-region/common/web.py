import json
import os
import threading
import time
from pathlib import Path

from flask import Flask, Response, jsonify, render_template, stream_with_context

from common.config import channel


class Feed:
    def __init__(self):
        self.lock = threading.Lock()
        self.state = None
        self.status = "Waiting for Valkey"
        self.source = "none"
        self.connected = False
        self.received_at = None

    def update(self, state, source):
        with self.lock:
            old = self.state
            if old and old["run_id"] == state["run_id"] and old["sequence"] >= state["sequence"]:
                return
            # Ignore delayed snapshots from a previous publisher process.
            if old and state["started_at"] < old["started_at"]:
                return
            self.state = state
            self.source = source
            self.received_at = time.time()

    def connection(self, connected, status):
        with self.lock:
            self.connected, self.status = connected, status

    def payload(self):
        with self.lock:
            age = None if self.state is None else max(0, time.time() - self.state["published_at"])
            return dict(state=self.state, status=self.status, connected=self.connected,
                        source=self.source, age_seconds=age,
                        stale=age is None or age > 5, received_at=self.received_at)


def create_app(role, feed):
    root = Path(__file__).resolve().parents[1]
    app = Flask(__name__, template_folder=str(root / "templates"), static_folder=str(root / "static"))

    @app.get("/")
    def index():
        return render_template("dashboard.html", role=role, channel=channel(),
                               region=os.getenv("REGION_LABEL", "Frankfurt" if role == "main" else "Amsterdam"))

    @app.get("/api/state")
    def state():
        return jsonify(feed.payload())

    @app.get("/healthz")
    def health():
        payload = feed.payload()
        healthy = payload["connected"] and not payload["stale"]
        return jsonify(ok=healthy, status=payload["status"], stale=payload["stale"]), 200 if healthy else 503

    @app.get("/events")
    def events():
        @stream_with_context
        def stream():
            while True:
                yield "data: " + json.dumps(feed.payload(), allow_nan=False) + "\n\n"
                time.sleep(0.25)
        return Response(stream(), mimetype="text/event-stream", headers={
            "Cache-Control": "no-cache", "X-Accel-Buffering": "no"})

    return app
