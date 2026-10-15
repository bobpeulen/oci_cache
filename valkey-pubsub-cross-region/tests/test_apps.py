import json
import random
import threading
import time
import unittest
from unittest.mock import patch

import fakeredis

from common.web import Feed, create_app
from main_app.app import run_game
from main_app.game import Game
from spectator_app.app import accept, subscribe


def eventually(predicate, timeout=4):
    end = time.monotonic() + timeout
    while time.monotonic() < end:
        if predicate():
            return
        time.sleep(0.02)
    raise AssertionError("Timed out waiting for background worker")


class GameTests(unittest.TestCase):
    def test_deuce_requires_two_point_lead_and_new_match_resets_score(self):
        game = Game(random.Random(42))
        game.score = [10, 10]
        game.point(0)
        self.assertEqual(game.phase, "playing")
        game.point(0)
        self.assertEqual(game.phase, "finished")
        self.assertEqual(game.wins, [1, 0])
        game.step(4)
        self.assertEqual(game.score, [0, 0])
        self.assertEqual(game.match, 2)
        self.assertEqual(game.total_points, [2, 0])

    def test_auto_play_produces_points_matches_and_bounded_ball(self):
        game = Game(random.Random(7))
        for _ in range(50000):
            game.step(0.05)
            self.assertTrue(0 <= game.x <= 1)
            self.assertTrue(0 <= game.y <= 1)
        self.assertGreater(sum(game.total_points), 20)
        self.assertGreater(sum(game.wins), 0)
        self.assertGreater(game.longest_rally, 0)
        self.assertEqual(game.snapshot()["sequence"], 1)
        self.assertEqual(game.snapshot()["sequence"], 2)


class FeedAndWebTests(unittest.TestCase):
    def test_duplicates_old_sequences_and_old_publisher_runs_ignored(self):
        feed = Feed()
        game = Game()
        first, second = game.snapshot(), game.snapshot()
        feed.update(second, "pubsub")
        feed.update(first, "replicated snapshot")
        feed.update(second, "replicated snapshot")
        self.assertEqual(feed.payload()["source"], "pubsub")
        old_run = dict(first, run_id="previous", started_at=game.started_at - 10)
        feed.update(old_run, "pubsub")
        self.assertEqual(feed.payload()["state"]["run_id"], game.run_id)

    def test_invalid_payload_does_not_break_next_valid_event(self):
        feed = Feed()
        for payload in ('invalid', 'null', '[]', '{"schema_version": 1}',
                        json.dumps(dict(Game().snapshot(), published_at=float("nan")))):
            accept(feed, payload, "pubsub")
        self.assertIsNone(feed.payload()["state"])
        accept(feed, json.dumps(Game().snapshot()), "pubsub")
        self.assertIsNotNone(feed.payload()["state"])

    def test_dashboards_api_sse_health_and_stale_detection(self):
        for role in ("main", "spectator"):
            feed = Feed()
            app = create_app(role, feed).test_client()
            page = app.get("/")
            self.assertEqual(page.status_code, 200)
            self.assertEqual(b'<canvas id="court"' in page.data, role == "main")
            self.assertEqual(app.get("/healthz").status_code, 503)
            state = Game().snapshot()
            feed.update(state, "pubsub")
            feed.connection(True, "Subscribed")
            self.assertEqual(app.get("/healthz").status_code, 200)
            self.assertEqual(app.get("/api/state").json["state"]["sequence"], 1)
            response = app.get("/events", buffered=False)
            self.assertTrue(next(response.response).startswith(b"data: "))
            response.close()
            with patch("common.web.time.time", return_value=state["published_at"] + 10):
                self.assertEqual(app.get("/healthz").status_code, 503)


class IntegrationTests(unittest.TestCase):
    def test_publisher_to_strict_pubsub_spectator_and_persisted_state(self):
        server = fakeredis.FakeServer()
        main_feed, spectator_feed = Feed(), Feed()
        stop = threading.Event()
        pub_client = fakeredis.FakeRedis(server=server, decode_responses=True)
        sub_client = fakeredis.FakeRedis(server=server, decode_responses=True)
        reader = fakeredis.FakeRedis(server=server, decode_responses=True)
        with patch("main_app.app.client", return_value=pub_client), \
             patch("spectator_app.app.client", return_value=sub_client), \
             patch.dict("os.environ", {"SNAPSHOT_FALLBACK": "false", "GAME_CHANNEL": "game.events", "GAME_STATE_KEY": "game:state"}):
            threads = [threading.Thread(target=subscribe, args=(spectator_feed, stop)),
                       threading.Thread(target=run_game, args=(main_feed, stop))]
            try:
                threads[0].start()
                eventually(lambda: spectator_feed.payload()["connected"])
                threads[1].start()
                eventually(lambda: spectator_feed.payload()["state"] is not None)
                self.assertEqual(spectator_feed.payload()["source"], "pubsub")
                self.assertEqual(json.loads(reader.get("game:state"))["run_id"],
                                 spectator_feed.payload()["state"]["run_id"])
                # An outage is visible, and both background workers reconnect.
                server.connected = False
                eventually(lambda: not main_feed.payload()["connected"])
                eventually(lambda: not spectator_feed.payload()["connected"])
                before = spectator_feed.payload()["state"]["sequence"]
                server.connected = True
                eventually(lambda: spectator_feed.payload()["connected"], timeout=6)
                eventually(lambda: spectator_feed.payload()["state"]["sequence"] > before)
            finally:
                server.connected = True
                stop.set()
                for thread in threads:
                    if thread.ident:
                        thread.join(timeout=5)
                self.assertTrue(all(not thread.is_alive() for thread in threads))

    def test_secondary_snapshot_works_without_forwarded_pubsub(self):
        # Separate logical clusters. Only a SET is copied to the secondary.
        # Application reads must never issue writes against this secondary.
        primary = fakeredis.FakeRedis(decode_responses=True)
        secondary = fakeredis.FakeRedis(decode_responses=True)
        snapshot = Game().snapshot()
        primary.set("game:state", json.dumps(snapshot))
        secondary.set("game:state", primary.get("game:state"))
        feed, stop = Feed(), threading.Event()
        with patch("spectator_app.app.client", return_value=secondary), \
             patch.dict("os.environ", {"SNAPSHOT_FALLBACK": "true", "GAME_STATE_KEY": "game:state"}), \
             patch.object(secondary, "set", side_effect=AssertionError("spectator wrote to secondary")), \
             patch.object(secondary, "publish", side_effect=AssertionError("spectator published")):
            thread = threading.Thread(target=subscribe, args=(feed, stop))
            thread.start()
            try:
                eventually(lambda: feed.payload()["state"] is not None)
                self.assertEqual(feed.payload()["source"], "replicated snapshot")
                self.assertEqual(feed.payload()["state"], snapshot)
            finally:
                stop.set()
                thread.join(timeout=5)


if __name__ == "__main__":
    unittest.main()
