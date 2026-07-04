"""One-command live dev server for the Omija demo pages.

    uv run python scripts/serve.py        # http://localhost:8000  (auto-rebuild + live reload)
    uv run python scripts/serve.py --no-watch   # serve current out/ only
    uv run python scripts/serve.py --port 9000

Regenerates every demo page from its generator whenever a source file
(scripts/, actions/, store/, adapter/, registry/, eval/) changes, then the
browser auto-refreshes. Landing page is the steady-state console.

Stdlib only (http.server + polling watcher) — no extra dependency, fully offline.
"""

from __future__ import annotations

import argparse
import subprocess
import sys
import threading
import time
from datetime import datetime
from functools import partial
from http.server import SimpleHTTPRequestHandler, ThreadingHTTPServer
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
OUT = ROOT / "out"

# generator script -> the page it writes (landing first)
GENERATORS = [
    "scripts/omija_console_home.py",
    "scripts/omija_demo.py",
    "scripts/data_coverage_map.py",
    "scripts/program_threat_view.py",
]
LANDING = "omija_console_home.html"

# directories whose .py/.yaml/.csv changes should trigger a rebuild
WATCH_DIRS = ["scripts", "actions", "store", "adapter", "registry", "eval"]
WATCH_SUFFIXES = {".py", ".yaml", ".yml", ".csv"}

# bumped on every successful rebuild; the injected reload snippet polls it
_version = str(time.time())
_build_lock = threading.Lock()

RELOAD_SNIPPET = """
<script>
(function(){
  let mine=null;
  async function tick(){
    try{
      const r=await fetch('/__version',{cache:'no-store'});
      const v=await r.text();
      if(mine===null){mine=v;}
      else if(v!==mine){location.reload();}
    }catch(e){}
  }
  setInterval(tick,1000); tick();
})();
</script>
"""


def _sources() -> list[Path]:
    files: list[Path] = []
    for d in WATCH_DIRS:
        for p in (ROOT / d).rglob("*"):
            if p.suffix in WATCH_SUFFIXES and "__pycache__" not in p.parts:
                files.append(p)
    return files


def _snapshot() -> dict[Path, float]:
    snap: dict[Path, float] = {}
    for p in _sources():
        try:
            snap[p] = p.stat().st_mtime
        except OSError:
            pass
    return snap


def rebuild(reason: str = "") -> bool:
    global _version
    with _build_lock:
        stamp = datetime.now().strftime("%H:%M:%S")
        tag = f" ({reason})" if reason else ""
        print(f"[{stamp}] rebuilding{tag} …", flush=True)
        ok = True
        for gen in GENERATORS:
            proc = subprocess.run(
                [sys.executable, str(ROOT / gen)],
                cwd=ROOT, capture_output=True, text=True,
            )
            name = Path(gen).name
            if proc.returncode != 0:
                ok = False
                err = (proc.stderr or proc.stdout).strip().splitlines()
                tail = err[-1] if err else "unknown error"
                print(f"    ✗ {name}: {tail}", flush=True)
            else:
                print(f"    ✓ {name}", flush=True)
        _version = str(time.time())
        print(f"[{stamp}] {'done' if ok else 'done WITH ERRORS'} — "
              f"http://localhost:{_PORT}/", flush=True)
        return ok


def watch_loop(interval: float = 0.7) -> None:
    prev = _snapshot()
    while True:
        time.sleep(interval)
        cur = _snapshot()
        if cur != prev:
            changed = [p for p in cur if prev.get(p) != cur[p]]
            new = [p for p in prev if p not in cur]
            first = (changed + new)[:1]
            reason = first[0].relative_to(ROOT).as_posix() if first else "change"
            rebuild(reason)
            prev = cur


class _InjectingHandler(SimpleHTTPRequestHandler):
    """Serve out/, injecting the live-reload poller into HTML responses."""

    def do_GET(self):  # noqa: N802
        if self.path == "/__version":
            self._send_bytes(_version.encode(), "text/plain")
            return
        if self.path in ("/", ""):
            self.send_response(302)
            self.send_header("Location", "/" + LANDING)
            self.end_headers()
            return
        path = self.translate_path(self.path)
        if path.endswith(".html") and Path(path).is_file():
            data = Path(path).read_bytes()
            snippet = RELOAD_SNIPPET.encode()
            data = (data.replace(b"</body>", snippet + b"</body>", 1)
                    if b"</body>" in data else data + snippet)
            self._send_bytes(data, "text/html; charset=utf-8")
            return
        return super().do_GET()

    def _send_bytes(self, data: bytes, content_type: str) -> None:
        self.send_response(200)
        self.send_header("Content-Type", content_type)
        self.send_header("Content-Length", str(len(data)))
        self.send_header("Cache-Control", "no-store")
        self.end_headers()
        self.wfile.write(data)

    def log_message(self, fmt, *args):
        msg = fmt % args if args else fmt
        if "/__version" in msg:
            return  # silence the 1 Hz reload poll
        sys.stderr.write(f"    {msg}\n")


_PORT = 8000


def main() -> int:
    global _PORT
    ap = argparse.ArgumentParser()
    ap.add_argument("--port", type=int, default=8000)
    ap.add_argument("--no-watch", action="store_true",
                    help="serve current out/ without rebuilding on change")
    ap.add_argument("--no-build", action="store_true",
                    help="skip the initial rebuild")
    args = ap.parse_args()
    _PORT = args.port

    if not args.no_build:
        rebuild("startup")

    if not args.no_watch:
        threading.Thread(target=watch_loop, daemon=True).start()

    handler = partial(_InjectingHandler, directory=str(OUT))
    server = ThreadingHTTPServer(("127.0.0.1", args.port), handler)
    print(f"\n  Omija dev server → http://localhost:{args.port}/")
    print(f"  landing: {LANDING}   |   watch: {'off' if args.no_watch else 'on'}"
          f"   |   Ctrl-C to stop\n")
    try:
        server.serve_forever()
    except KeyboardInterrupt:
        print("\nstopped.")
    return 0


if __name__ == "__main__":
    sys.exit(main())
