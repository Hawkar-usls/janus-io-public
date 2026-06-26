(function () {
  "use strict";

  const DEFAULT_URL = "a18_hrain_swarm_overlay.json";
  const REQUIRED_SENTINELS = [
    "observer_only",
    "miner_untouched",
    "wire_hash_submit_frozen",
    "mirror_untouched",
  ];

  function asArray(value) {
    return Array.isArray(value) ? value : [];
  }

  function text(value, fallback) {
    if (value === null || value === undefined || value === "") return fallback || "-";
    return String(value);
  }

  function checkSentinels(payload) {
    const missing = [];
    for (const key of REQUIRED_SENTINELS) {
      if (payload[key] !== true) missing.push(key);
    }
    return {
      ok: missing.length === 0,
      missing,
    };
  }

  function normalizeNode(raw) {
    const health = text(raw.health || raw.status || raw.state, "unknown");
    const online = raw.online === true || ["live", "online", "ok", "healthy", "active"].includes(health.toLowerCase());
    return {
      id: text(raw.node_id || raw.id || raw.name || raw.node, "unknown"),
      role: text(raw.role || raw.kind || raw.type, "swarm_node"),
      online,
      health,
      rssi: raw.rssi ?? raw.wifi_rssi ?? null,
      uptime: raw.uptime ?? raw.uptime_ms ?? null,
      hashRate: raw.hash_rate ?? raw.hashrate ?? raw.H ?? null,
      bestBits: raw.best_bits ?? raw.bestBits ?? raw.best_z ?? null,
      accepted: raw.accepted ?? raw.shares ?? null,
      rejected: raw.rejected ?? raw.rejects ?? null,
      trust: raw.trust ?? raw.swarmTrust ?? null,
      stress: raw.stress ?? raw.localStress ?? null,
      dopamine: raw.dopamine ?? null,
      oxytokin: raw.oxytokin ?? raw.oxy ?? null,
      audioMode: raw.audio_mode ?? raw.audio ?? null,
      presence: raw.presence ?? null,
      camera: raw.camera ?? null,
      textcast: raw.textcast ?? raw.ssid_textcast ?? null,
    };
  }

  function normalizeOverlay(payload) {
    const sentinels = checkSentinels(payload || {});
    const nodes = asArray(payload && payload.nodes).filter(Boolean).map(normalizeNode);
    const events = asArray(payload && payload.events);
    const alerts = asArray(payload && payload.alerts);
    const summary = payload && typeof payload.summary === "object" && payload.summary ? payload.summary : {};
    return {
      ok: true,
      offline: false,
      sentinels,
      source: text(payload && payload.source, "NAS_Brain/Buzz/ESP32_M5_swarm"),
      nodes,
      events,
      alerts,
      summary: {
        nodesKnown: Number(summary.nodes_known ?? nodes.length),
        nodesLive: Number(summary.nodes_live ?? nodes.filter((node) => node.online).length),
        endpointErrors: summary.endpoint_errors || {},
        tranceptionStatus: summary.tranception_status || {},
      },
      raw: payload,
    };
  }

  function offlineOverlay(reason) {
    return {
      ok: false,
      offline: true,
      sentinels: { ok: false, missing: REQUIRED_SENTINELS.slice() },
      source: "A18 bridge offline",
      nodes: [],
      events: [],
      alerts: [{ kind: "overlay_offline", message: reason || "missing overlay" }],
      summary: { nodesKnown: 0, nodesLive: 0, endpointErrors: {}, tranceptionStatus: {} },
      raw: null,
    };
  }

  async function fetchOverlay(url) {
    try {
      const response = await fetch(url || DEFAULT_URL, { cache: "no-store" });
      if (!response.ok) return offlineOverlay(`HTTP ${response.status}`);
      const payload = await response.json();
      return normalizeOverlay(payload);
    } catch (error) {
      return offlineOverlay(error && error.message ? error.message : "fetch failed");
    }
  }

  function statusClass(model) {
    if (model.offline) return "a18-swarm-offline";
    if (!model.sentinels.ok) return "a18-swarm-warn";
    if (model.summary.nodesLive > 0) return "a18-swarm-online";
    return "a18-swarm-idle";
  }

  function renderBadge(target, model) {
    if (!target) return;
    const state = model.offline ? "offline" : model.sentinels.ok ? "online" : "warn";
    target.className = `a18-swarm-badge ${statusClass(model)}`;
    target.textContent = `SWARM: ${state.toUpperCase()} ${model.summary.nodesLive}/${model.summary.nodesKnown}`;
    target.title = model.sentinels.ok ? "A18 observer sentinels OK" : `A18 sentinel warning: ${model.sentinels.missing.join(", ")}`;
  }

  function nodeLine(node) {
    const rssi = node.rssi === null || node.rssi === undefined ? "-" : `${node.rssi} dBm`;
    const tail = node.bestBits === null || node.bestBits === undefined ? "" : ` z${node.bestBits}`;
    const social = [
      node.trust === null || node.trust === undefined ? "" : `T${node.trust}`,
      node.stress === null || node.stress === undefined ? "" : `S${node.stress}`,
      node.oxytokin === null || node.oxytokin === undefined ? "" : `O${node.oxytokin}`,
    ].filter(Boolean).join(" ");
    return `<div class="a18-swarm-node ${node.online ? "is-online" : "is-offline"}">
      <span class="a18-dot"></span>
      <strong>${escapeHtml(node.id)}</strong>
      <em>${escapeHtml(node.role)}</em>
      <span>${escapeHtml(node.health)} / ${escapeHtml(rssi)}${escapeHtml(tail)}</span>
      <small>${escapeHtml(social || "-")}</small>
    </div>`;
  }

  function renderPanel(target, model) {
    if (!target) return;
    const alerts = model.alerts.slice(0, 6).map((alert) => `<li>${escapeHtml(text(alert.kind, "alert"))}: ${escapeHtml(text(alert.node_id || alert.message, "-"))}</li>`).join("");
    const nodes = model.nodes.slice(0, 24).map(nodeLine).join("");
    target.className = `a18-swarm-panel ${statusClass(model)}`;
    target.innerHTML = `
      <header>
        <span>A18 Home Swarm</span>
        <b>${model.summary.nodesLive}/${model.summary.nodesKnown}</b>
      </header>
      <section class="a18-swarm-nodes">${nodes || "<p>No nodes visible.</p>"}</section>
      <section class="a18-swarm-alerts"><ul>${alerts || "<li>No alerts.</li>"}</ul></section>
    `;
  }

  function renderTicker(target, model) {
    if (!target) return;
    const items = model.events.slice(0, 8).map((event) => {
      const label = `${text(event.kind, "event")} ${text(event.node_id, "")}`.trim();
      return `<span>${escapeHtml(label)}</span>`;
    }).join("");
    target.className = "a18-swarm-ticker";
    target.innerHTML = items || "<span>A18 swarm quiet</span>";
  }

  function escapeHtml(value) {
    return String(value)
      .replace(/&/g, "&amp;")
      .replace(/</g, "&lt;")
      .replace(/>/g, "&gt;")
      .replace(/"/g, "&quot;");
  }

  function render(model, targets) {
    const t = targets || {};
    renderBadge(t.badge || document.querySelector("[data-a18-swarm-badge]"), model);
    renderPanel(t.panel || document.querySelector("[data-a18-swarm-panel]"), model);
    renderTicker(t.ticker || document.querySelector("[data-a18-swarm-ticker]"), model);
    if (typeof t.onData === "function") t.onData(model);
    window.JANUS_A18_SWARM_OVERLAY_MODEL = model;
  }

  async function start(options) {
    const cfg = Object.assign({ url: DEFAULT_URL, intervalMs: 6500, targets: null }, options || {});
    async function tick() {
      const model = await fetchOverlay(cfg.url);
      render(model, cfg.targets);
      return model;
    }
    const first = await tick();
    if (cfg.intervalMs > 0) {
      window.setInterval(tick, cfg.intervalMs);
    }
    return first;
  }

  window.JANUS_A18_HRAIN_SWARM_OVERLAY = {
    fetchOverlay,
    normalizeOverlay,
    checkSentinels,
    render,
    start,
  };
})();
