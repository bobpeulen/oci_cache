import json
import logging
import math
import os
import threading
import time

from redis.exceptions import RedisError
from waitress import serve

from common.config import channel, client, configure, number, state_key
from common.web import Feed, create_app

log = logging.getLogger(__name__)


def accept(feed, payload, source):
    try:
        state = json.loads(payload)
        if not isinstance(state, dict) or state.get("schema_version") != 1:
            raise ValueError("unsupported schema")
        for key in ("started_at", "published_at", "sequence"):
            if not isinstance(state[key], (int, float)) or not math.isfinite(state[key]):
                raise ValueError("invalid timing or sequence")
        if not isinstance(state["run_id"], str):
            raise ValueError("invalid run")
        for key in ("players", "score", "wins", "total_points", "hits", "paddles"):
            if len(state[key]) != 2:
                raise ValueError("invalid players")
        for key in ("match", "rally", "longest_rally", "phase", "last_event", "ball"):
            if key not in state:
                raise ValueError("incomplete event")
        feed.update(state, source)
    except (ValueError, TypeError, KeyError, OverflowError):
        log.warning("Ignoring malformed game event")


def subscribe(feed, stop):
    cache = client()
    fallback = os.getenv("SNAPSHOT_FALLBACK", "true").lower() == "true"
    poll_interval = number("SNAPSHOT_POLL_INTERVAL", "1")
    while not stop.is_set():
        try:
            with cache.pubsub() as pubsub:
                pubsub.subscribe(channel())
                next_poll = 0
                while not stop.is_set():
                    message = pubsub.get_message(timeout=0.25)
                    if message:
                        feed.connection(True, "Subscribed to " + channel())
                        if message["type"] == "message":
                            accept(feed, message["data"], "pubsub")
                    # Periodic GET also detects connection failures while the channel is idle.
                    if time.monotonic() >= next_poll:
                        if fallback:
                            payload = cache.get(state_key())
                            if payload:
                                accept(feed, payload, "replicated snapshot")
                        else:
                            cache.ping()
                        next_poll = time.monotonic() + poll_interval
        except RedisError as exc:
            feed.connection(False, "Valkey unavailable · reconnecting")
            log.warning("Subscription failed (%s); retrying in 2 seconds", type(exc).__name__)
            stop.wait(2)
    cache.close()


def main():
    configure("spectator")
    logging.basicConfig(level=logging.INFO)
    feed, stop = Feed(), threading.Event()
    worker = threading.Thread(target=subscribe, args=(feed, stop), daemon=True)
    worker.start()
    try:
        serve(create_app("spectator", feed), host=os.getenv("APP_HOST", "0.0.0.0"),
              port=int(os.getenv("APP_PORT", "5001")), threads=32)
    finally:
        stop.set()
        worker.join(timeout=5)


if __name__ == "__main__":
    main()
