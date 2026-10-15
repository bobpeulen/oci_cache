import json
import logging
import os
import threading
import time

from redis.exceptions import RedisError
from waitress import serve

from common.config import channel, client, configure, number, state_key
from common.web import Feed, create_app
from main_app.game import Game

log = logging.getLogger(__name__)


def run_game(feed, stop):
    cache = client()
    game = Game()
    interval = number("PUBLISH_INTERVAL", "0.25")
    next_publish = 0
    while not stop.wait(0.05):
        game.step(0.05)
        if time.monotonic() < next_publish:
            continue
        state = game.snapshot()
        try:
            payload = json.dumps(state, allow_nan=False)
            # Store before announcing. No writes ever occur in the spectator.
            with cache.pipeline(transaction=True) as pipe:
                pipe.set(state_key(), payload)
                pipe.publish(channel(), payload)
                pipe.execute()
            feed.update(state, "publisher")
            feed.connection(True, "Publishing to Valkey")
            next_publish = time.monotonic() + interval
        except RedisError as exc:
            feed.connection(False, "Valkey unavailable · retrying")
            log.warning("Publish failed (%s); retrying in 2 seconds", type(exc).__name__)
            next_publish = time.monotonic() + 2
    cache.close()


def main():
    configure("main")
    logging.basicConfig(level=logging.INFO)
    feed, stop = Feed(), threading.Event()
    worker = threading.Thread(target=run_game, args=(feed, stop), daemon=True)
    worker.start()
    try:
        serve(create_app("main", feed), host=os.getenv("APP_HOST", "0.0.0.0"),
              port=int(os.getenv("APP_PORT", "5000")), threads=32)
    finally:
        stop.set()
        worker.join(timeout=5)


if __name__ == "__main__":
    main()
