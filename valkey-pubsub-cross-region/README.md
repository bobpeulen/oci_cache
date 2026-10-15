# Cross Court: ping pong across OCI Cache regions

Two small Python/Flask applications. No direct communication between VMs and no replication setup is performed by this project.

```text
Frankfurt VM                       OCI Cache Frankfurt
main_app:5000 ── SET game:state ──► primary cluster
             └─ PUBLISH game.events ─┘
                                         │ OCI cross-region replication
                                         ▼
Amsterdam VM                       OCI Cache Amsterdam
spectator_app:5001 ◄─ SUBSCRIBE ──── secondary cluster
                  ◄─ GET game:state (startup/recovery)
```

The main app automatically plays simplified ping pong: random returns and misses, first to 11 with a two point lead, then another match after a short pause. Its dashboard animates the game. The spectator shows only the score and statistics: points, paddle returns, rally lengths, match wins, event sequence, data age and delivery source. Both dashboards update over server-sent events (SSE), without browser refreshes.

## Pub/Sub and cross-region replication

The publisher uses ordinary `PUBLISH game.events <JSON>`; the spectator uses ordinary `SUBSCRIBE game.events`. These are **not** sharded `SPUBLISH`/`SSUBSCRIBE` commands.

[Oracle documents cross-region replication of data](https://docs.oracle.com/en-us/iaas/Content/ocicache/cross-region-replication.htm), but that page does not explicitly guarantee cross-region forwarding of Pub/Sub messages. Test that behavior on your clusters using the CLI steps below. Do not infer it from successful key replication. This project does not claim to validate OCI's behavior locally.

To support late starts, reconnects, and deployments where messages do not cross regions, the main app also stores the full latest snapshot in `game:state`. The spectator reads that key every second by default, from **its own Amsterdam cluster only**. This also makes the dashboard work through native data replication without a relay service. The dashboard explicitly labels updates as **Valkey Pub/Sub** or **Replicated snapshot (GET)**. A snapshot read does not recover every missed event: the latest totals and score are recovered.

Set `SNAPSHOT_FALLBACK=false` in `spectator.env` to test strictly through Pub/Sub, with no snapshot reads. Pub/Sub has no replay, and events sent while a subscriber is disconnected are lost. If data replicates but messages do not, strict mode waits for events; use the snapshot mode for the working demo. Cross-region updates are asynchronous and may be delayed.

## Install on each Linux VM

Use Python **3.10 or newer**. Copy this project to each VM, for example `/opt/pingpong`, then run these commands from that directory:

```bash
python3 --version
python3 -m venv .venv
source .venv/bin/activate
python -m pip install -r requirements.txt
```

If `venv` is missing on Ubuntu, install `python3-venv` using your OS package manager. On Oracle Linux, install an available Python 3.10+ package and use its executable (for example `python3.11`) to create the environment. The apps use the Valkey-compatible `redis-py` library; they do not shell out to `valkey-cli`.

### Frankfurt: main app

```bash
cp main.env.example main.env
chmod 600 main.env
nano main.env
python -m main_app.app
```

Set `VALKEY_HOST` to the **Frankfurt primary endpoint FQDN**, and fill in `VALKEY_USERNAME` / `VALKEY_PASSWORD` if your cluster requires authentication. Leave unused credential fields blank. Open `http://<frankfurt-vm-ip>:5000`.

### Amsterdam: spectator

```bash
cp spectator.env.example spectator.env
chmod 600 spectator.env
nano spectator.env
python -m spectator_app.app
```

Set `VALKEY_HOST` to the **Amsterdam secondary cluster's endpoint FQDN** and use credentials configured on that cluster. The spectator only reads/subscribes; it never writes to the secondary or connects to Frankfurt. Open `http://<amsterdam-vm-ip>:5001`.

Use the same `GAME_CHANNEL` and `GAME_STATE_KEY` in both files. A single game publisher should use this channel/key pair. For another independent game, use another pair and another port. Run **one process per app**; each process starts its own background worker. Use the provided `python -m ...` entry points, which run Waitress with Flask; do not use a debug reloader or multiple publisher workers.

### Connection settings

Edit the `.env` file for that app, then restart it. Existing environment variables override file values. The files are resolved relative to the project, independent of the current working directory.

| Setting | Default / purpose |
| --- | --- |
| `VALKEY_HOST` | Cluster FQDN; `localhost` when unset |
| `VALKEY_PORT` | `6379` |
| `VALKEY_TLS` | `true`; use `false` only for a local non-TLS server |
| `VALKEY_USERNAME`, `VALKEY_PASSWORD` | Optional ACL credentials, separate for each cluster |
| `VALKEY_CA_CERT` | Optional CA bundle path; otherwise system trust roots |
| `GAME_CHANNEL` | `game.events` |
| `GAME_STATE_KEY` | `game:state`, overwritten with the latest full snapshot |
| `APP_HOST` | `0.0.0.0` |
| `APP_PORT` | Main `5000`, spectator `5001` |
| `REGION_LABEL` | Dashboard region label |
| `PUBLISH_INTERVAL` | Main only; `0.25` seconds (4 updates/sec) |
| `SNAPSHOT_FALLBACK` | Spectator only; `true` enables replicated-state recovery |
| `SNAPSHOT_POLL_INTERVAL` | Spectator only; `1` second |

TLS verifies both the certificate and hostname. Use the OCI FQDN rather than an IP address. This example uses non-sharded clusters, which Oracle currently requires for cross-region replication. If you use OCI IAM authentication, this app does not generate or refresh IAM tokens; provide a valid token through `VALKEY_PASSWORD` and restart after updating it, or use an appropriate configured ACL user for this demo.

[OCI connection documentation](https://docs.oracle.com/en-us/iaas/Content/ocicache/connecttocluster.htm) describes private endpoints and TLS. Each VM needs a network route to its local cache and access to TCP 6379. To view the dashboards remotely, allow TCP 5000 or 5001 as appropriate through the VM firewall and OCI NSG/security list, scoped to your IP. Alternatively, bind `APP_HOST=127.0.0.1` and use SSH forwarding:

```bash
ssh -L 5000:127.0.0.1:5000 opc@<frankfurt-vm-ip>
# In a separate terminal:
ssh -L 5001:127.0.0.1:5001 opc@<amsterdam-vm-ip>
```

Then browse `http://localhost:5000` and `http://localhost:5001`. The dashboards have no login or game controls; use private networking or SSH for a private demo.

### Run as a service (optional)

The supplied systemd template assumes `/opt/pingpong` and user `opc`. Change `User` and paths for your VM; make sure that user owns/can read the project and its `.env` file.

```bash
sudo cp deploy/pingpong@.service /etc/systemd/system/
sudo systemctl daemon-reload
# Frankfurt VM:
sudo systemctl enable --now pingpong@main
# Amsterdam VM instead:
sudo systemctl enable --now pingpong@spectator
```

Use `journalctl -u pingpong@main -f` or `journalctl -u pingpong@spectator -f` for logs. Restart the appropriate service after connection changes. Do not also run the app manually on the same VM/port.

## Verify the cloud flow with valkey-cli

Use your actual endpoints. The commands below assume no authentication; if required, add `--user <username> --askpass` to each command. This prompts for the password instead of exposing it in the shell command. Add `--cacert /path/to/ca.pem` if using a custom CA.

1. Check connections from each VM to its local cache:

   ```bash
   # Frankfurt VM
   valkey-cli --tls -h <frankfurt-endpoint> -p 6379 PING
   # Amsterdam VM
   valkey-cli --tls -h <amsterdam-endpoint> -p 6379 PING
   ```

2. On Amsterdam, keep a subscriber running **before** publishing:

   ```bash
   valkey-cli --tls -h <amsterdam-endpoint> SUBSCRIBE game.events
   ```

3. In Frankfurt, start the main app, or test transport explicitly:

   ```bash
   valkey-cli --tls -h <frankfurt-endpoint> PUBLISH game.events '{"probe":"Frankfurt to Amsterdam"}'
   ```

   The CLI subscriber should show that probe **if your OCI setup forwards Pub/Sub across regions**. The spectator app intentionally ignores this probe because it is not a full game event. A `PUBLISH` return value is a local subscriber count, not a cross-region delivery receipt.

4. With the main app running, inspect replicated game data in Amsterdam:

   ```bash
   valkey-cli --tls -h <amsterdam-endpoint> GET game:state
   ```

   Repeat and check that `sequence` increases. If the key changes but the CLI subscriber receives no messages, data replication works but Pub/Sub forwarding has not been demonstrated. Keep `SNAPSHOT_FALLBACK=true` to display the replicated statistics.

5. Start the spectator. Check **Delivery**, **Event sequence**, and data age on its dashboard. Stop the main app: after five seconds, both dashboards show stale data rather than presenting an old score as live. Restart it to begin a new session. The background workers automatically reconnect to Valkey following connection failures.

## Local demonstration

An optional Compose file starts a **single** Valkey; it does not simulate OCI cross-region replication:

```bash
docker compose up -d
cp main.env.example main.env
cp spectator.env.example spectator.env
```

In **both** files, set `VALKEY_HOST=localhost` and `VALKEY_TLS=false`; leave authentication fields empty. Then, in two activated virtual-environment terminals:

```bash
python -m main_app.app
# Second terminal:
python -m spectator_app.app
```

Visit ports 5000 and 5001. This validates normal Pub/Sub end to end against a local server. Stop local Valkey with `docker compose down`; its named volume retains stored data.

## Event data and endpoints

Every event is a full JSON snapshot, including `schema_version`, publisher `run_id`, `started_at`, monotonically increasing `sequence` within that run, `published_at` (Unix UTC seconds), `players`, `score`, `wins`, `total_points`, `hits`, `rally`, `longest_rally`, `phase`, `last_event`, `ball`, and `paddles`. Match wins and totals cover the current publisher process; restarting it starts a fresh session. A single atomic Valkey transaction stores the snapshot and publishes the identical JSON payload. No event history is stored.

The spectator ignores duplicates and older snapshots. Keep VM clocks synchronized: data age is measured from the publisher timestamp, and publisher start timestamps distinguish process restarts. Freshness is a five second window, so choose update/poll intervals below that for the demo.

Both apps expose:

| Route | Purpose |
| --- | --- |
| `/` | Dashboard |
| `/api/state` | Latest in-memory view of Valkey data and connection/freshness metadata |
| `/events` | SSE feed for browsers |
| `/healthz` | HTTP 200 when connected with fresh data; 503 otherwise |

Waitress runs 32 threads; each open SSE dashboard uses one thread. This is sized for a small demo. If using a reverse proxy, disable buffering for `/events` and allow long-running responses.

## Tests

```bash
python -m pip install -r requirements-dev.txt
python -m unittest discover -s tests -v
```

Tests cover game rules, automatic progression, dashboard/API/SSE responses, stale data, event validation, duplicate ordering, Pub/Sub publishing and subscribing, connection outage recovery, and separate-cluster snapshot recovery with no subscriber writes. Integration tests use `fakeredis`; they do not verify OCI replication or TLS. Use the CLI checks above on your VMs for that validation.
