"use strict";
const el = (id) => document.getElementById(id);
const put = (id, value) => { el(id).textContent = value; };
let latest = null;
let lastPacketAt = 0;
const sources = {publisher: "Published to Valkey", pubsub: "Valkey Pub/Sub", "replicated snapshot": "Replicated snapshot (GET)"};
const stream = new EventSource("/events");
stream.onmessage = (event) => {
  const payload = JSON.parse(event.data);
  lastPacketAt = Date.now();
  el("indicator").classList.toggle("live", payload.connected && !payload.stale);
  put("status", payload.stale && payload.state ? "Game data is stale · " + payload.status : payload.status);
  put("age", payload.age_seconds === null ? "Waiting for the first event" : `${payload.age_seconds.toFixed(1)}s since publication`);
  if (!payload.state) return;
  const s = payload.state;
  latest = s;
  for (let i = 0; i < 2; i++) { put(`player${i}`, s.players[i]); put(`score${i}`, s.score[i]); }
  put("match", `MATCH ${s.match}`);
  put("phase", s.phase === "finished" ? "Match complete · next match shortly" : "First to 11 · win by 2");
  put("last-event", s.last_event);
  put("rally", s.rally);
  put("longest", s.longest_rally);
  put("points", s.total_points[0] + s.total_points[1]);
  put("point-split", `${s.total_points[0]} / ${s.total_points[1]} · Ada / Linus`);
  put("wins", s.wins.join(" / "));
  put("hits", s.hits.join(" / "));
  put("source", sources[payload.source] || payload.source);
  put("sequence", s.sequence);
  put("published", new Date(s.published_at * 1000).toLocaleTimeString());
};
stream.onerror = () => { el("indicator").classList.remove("live"); put("status", "Dashboard disconnected · reconnecting…"); };
setInterval(() => {
  if (lastPacketAt && Date.now() - lastPacketAt > 5000) {
    el("indicator").classList.remove("live");
    put("status", "Dashboard disconnected · reconnecting…");
  }
}, 1000);
const canvas = el("court");
if (canvas) {
  const ctx = canvas.getContext("2d");
  let shown = {x: 0.5, y: 0.5};
  function draw() {
    const w = canvas.width, h = canvas.height;
    ctx.clearRect(0, 0, w, h);
    ctx.strokeStyle = "#3c5b4b";
    ctx.lineWidth = 2;
    ctx.setLineDash([8, 10]);
    ctx.beginPath(); ctx.moveTo(w / 2, 0); ctx.lineTo(w / 2, h); ctx.stroke();
    ctx.setLineDash([]);
    if (latest) {
      shown.x += (latest.ball.x - shown.x) * 0.2;
      shown.y += (latest.ball.y - shown.y) * 0.2;
      [0, 1].forEach((i) => {
        ctx.fillStyle = i ? "#8ccff2" : "#c1f489";
        ctx.fillRect(w * (i ? 0.95 : 0.05) - 5, latest.paddles[i] * h - h * 0.1, 10, h * 0.2);
      });
      ctx.fillStyle = "#ffffff";
      ctx.beginPath(); ctx.arc(shown.x * w, shown.y * h, 7, 0, Math.PI * 2); ctx.fill();
    }
    requestAnimationFrame(draw);
  }
  draw();
}
