#!/usr/bin/env python3
# -*- coding: utf-8 -*-
from __future__ import annotations
import argparse, os, socket, subprocess, sys, threading, time, webbrowser
from http.server import ThreadingHTTPServer, SimpleHTTPRequestHandler
from pathlib import Path
import json

class Handler(SimpleHTTPRequestHandler):
    def end_headers(self):
        self.send_header("Cache-Control", "no-store, no-cache, must-revalidate, max-age=0")
        self.send_header("Pragma", "no-cache")
        super().end_headers()
    def log_message(self, fmt, *args): return

def free_port(host, start):
    for p in range(start, start+40):
        s=socket.socket()
        try:
            s.bind((host,p)); s.close(); return p
        except OSError:
            s.close()
    return start

def stream(proc):
    assert proc.stdout is not None
    for line in proc.stdout:
        print(line.rstrip(), flush=True)

def ensure_json(path: Path, obj):
    if not path.exists():
        path.write_text(json.dumps(obj, ensure_ascii=False, indent=2), encoding="utf-8")

def main():
    ap=argparse.ArgumentParser()
    ap.add_argument("--host", default="127.0.0.1")
    ap.add_argument("--port", type=int, default=8797)
    ap.add_argument("--root", default="..")
    ap.add_argument("--no-open", action="store_true")
    args=ap.parse_args()
    here=Path(__file__).resolve().parent
    os.chdir(here)
    root=(here/args.root).resolve()
    graph=here/"a17_hrain_graph.json"
    status=here/"a17_status.json"
    bias=here/"temple_route_bias.json"
    bus=here/"sidecar_bus.json"
    matrix=here/"route_transition_matrix.json"
    hyp=here/"janus_demiurge_hypotheses.json"
    state=here/"a17_offsets.json"

    ensure_json(graph, {"version":"A17_INIT","nodes":[{"id":"HRAIN_CORE","label":"HRAIN CORE","kind":"core","group":"core","score":100}],"links":[]})
    ensure_json(status, {"version":"A17_INIT","stage":"starting","message":"waiting for worker","mtime":time.time()})
    ensure_json(bias, {"version":"A17_INIT","janus_route_bias":{},"observer_only":True})
    ensure_json(bus, {"version":"A17_INIT","sidecar_bus":{}})
    ensure_json(matrix, {"version":"A17_INIT","transitions":[]})
    ensure_json(hyp, {"version":"A17_INIT","hypotheses":[]})

    port=free_port(args.host,args.port)
    url=f"http://{args.host}:{port}/index.html"
    print("============================================================", flush=True)
    print(" A17.5 HRAIN JANUS GALAXY PRESENTATION", flush=True)
    print("============================================================", flush=True)
    print("[A17.6] Janus Galaxy presentation UI + HRain cluster LOD + VIDEO_SAFE.", flush=True)
    print("[A17] Demiurge sidecar: observer-only, tail-only, output-only.", flush=True)
    print("[A17] NOT stratum proxy. WIRE/HASH/SUBMIT frozen. Mirror untouched.", flush=True)
    print(f"[A17] folder: {here}", flush=True)
    print(f"[A17] scan root: {root}", flush=True)
    print(f"[A17] open: {url}", flush=True)

    srv=ThreadingHTTPServer((args.host,port), Handler)
    threading.Thread(target=srv.serve_forever, daemon=True).start()
    if not args.no_open:
        try: webbrowser.open(url, new=2)
        except Exception: pass

    cmd=[sys.executable, str(here/"a17_sidecar_shell_worker.py"),
         "--root", str(root),
         "--graph", str(graph),
         "--bias", str(bias),
         "--status", str(status),
         "--state", str(state),
         "--bus", str(bus),
         "--matrix", str(matrix),
         "--hypotheses", str(hyp),
         "--poll", "4",
         "--max-files", "160",
         "--initial-tail-bytes", "800000",
         "--max-read-bytes", "260000",
         "--max-lines-per-file", "1800",
         "--max-nodes", "1200",
         "--max-links", "1800"]
    print("[A17] worker:", " ".join(cmd), flush=True)
    proc=subprocess.Popen(cmd, stdout=subprocess.PIPE, stderr=subprocess.STDOUT, text=True, encoding="utf-8", errors="replace")
    threading.Thread(target=stream, args=(proc,), daemon=True).start()
    try:
        while True:
            time.sleep(10)
            if proc.poll() is None:
                print("[A17 heartbeat] worker running; server alive", flush=True)
            else:
                print(f"[A17 heartbeat] worker exited={proc.returncode}; server alive", flush=True)
                break
    except KeyboardInterrupt:
        print("\n[A17] stopped", flush=True)
        try: proc.terminate()
        except Exception: pass
        srv.shutdown()
    return 0

if __name__=="__main__":
    raise SystemExit(main())
