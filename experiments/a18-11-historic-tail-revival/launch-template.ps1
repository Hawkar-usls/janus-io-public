# Public-safe A18.11 launch template.
# This is intentionally not a ready-to-run miner script.
# Fill private pool, worker, and local paths only in a private checkout.

$RUN_NAME = "A18_11_HISTORIC_TAIL_REVIVAL_V1"
$WORKER = "<WORKER_LABEL>"
$POOL_HOST = "<POOL_HOST>"
$POOL_PORT = "<POOL_PORT>"
$POOL_USER = "<POOL_USER_OR_WALLET_WORKER>"
$POOL_PASS = "<POOL_PASSWORD>"

$ArgsList = @(
  "<PRIVATE_MINER_SCRIPT>",
  "--host", $POOL_HOST,
  "--port", $POOL_PORT,
  "--user", $POOL_USER,
  "--password", $POOL_PASS,
  "--suggest-diff", "<DIFFICULTY>",
  "--a11-full-janus",
  "--a12-noncemap-arc",
  "--a14-multiverse-navigator",
  "--mode", "proof",
  "--matrix", "canonical",
  "--local-submit-z", "0",
  "--no-auto-escalate-local-z",
  "--no-lowdiff-jump-to-floor",
  "--strict-50-50-randomized-traversal-mirror",
  "--workers", "16",
  "--batch", "100000",
  "--io-run-name", $RUN_NAME,
  "--signal-z", "28",
  "--tail-z", "30",
  "--tail-z33", "33",
  "--janus-glyph-accepted-link-min-z", "28",
  "--rare-tail-timing-min-z", "32",
  "--summary-every-rounds", "5",
  "--summary-every-seconds", "120",
  "--a11-calibration-accepted", "35",
  "--a11-evaluation-accepted", "250",
  "--a11-exploration-floor", "0.10",
  "--a11-historical-prior-weight", "0.07",
  "--linear-proof-weight", "32",
  "--janus-weight", "34",
  "--dual-lock-weight", "18",
  "--zim-s6-weight", "16",
  "--dual-lock-linear-s6-weight", "38",
  "--dual-lock-zim-s6-weight", "42",
  "--dual-lock-knight-s11-weight", "20",
  "--a14-nav-lock-after-accepted", "6",
  "--a14-nav-lock-prob", "0.78",
  "--a14-nav-explore-floor", "0.045",
  "--a14-nav-topk", "16",
  "--a14-nav-min-mh", "0.08",
  "--a14-nav-rollback-window", "44",
  "--a14-nav-prefer-route", "a14_navigator:janus_dispatcher::bitrev/s7/canonical",
  "--a14-nav-prefer-boost", "0.22",
  "--a9-min-random-control-mh", "25"
)

Write-Host "Template only. Do not run this file as-is."
