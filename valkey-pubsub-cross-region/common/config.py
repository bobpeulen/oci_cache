import math
import os
from pathlib import Path

import redis
from dotenv import load_dotenv


def configure(role):
    # A different file on each VM; existing environment variables take precedence.
    load_dotenv(Path(__file__).resolve().parents[1] / f"{role}.env")


def number(name, default):
    value = float(os.getenv(name, default))
    if not math.isfinite(value) or value <= 0:
        raise ValueError(f"{name} must be positive")
    return value


def client():
    options = dict(
        host=os.getenv("VALKEY_HOST", "localhost"),
        port=int(os.getenv("VALKEY_PORT", "6379")),
        username=os.getenv("VALKEY_USERNAME") or None,
        password=os.getenv("VALKEY_PASSWORD") or None,
        db=0,
        decode_responses=True,
        socket_connect_timeout=3,
        socket_timeout=3,
        health_check_interval=15,
    )
    if os.getenv("VALKEY_TLS", "true").lower() == "true":
        options.update(ssl=True, ssl_cert_reqs="required", ssl_check_hostname=True)
        if os.getenv("VALKEY_CA_CERT"):
            options["ssl_ca_certs"] = os.environ["VALKEY_CA_CERT"]
    return redis.Redis(**options)


def channel():
    return os.getenv("GAME_CHANNEL", "game.events")


def state_key():
    return os.getenv("GAME_STATE_KEY", "game:state")
