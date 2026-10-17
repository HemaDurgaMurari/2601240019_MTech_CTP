"""HTTP API + static frontend (stdlib only).  Run: python server.py  ->  http://127.0.0.1:8000"""
import argparse, asyncio, json, mimetypes, re, sqlite3, threading
from dataclasses import asdict
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer
from pathlib import Path
from mfa import DB, FACTORS, TRANSITIONS, InvalidTransition, Service, State

WEB = Path(__file__).parent / "web"
ROOT = Path(__file__).parent
LOOP = asyncio.new_event_loop()  # all service/state-machine work runs on this one asyncio loop
threading.Thread(target=LOOP.run_forever, daemon=True).start()


async def api(svc, m, path, b):
    if path == "/api/state":
        users = []
        for u in svc.db.q("select name from users"):
            a = svc.acct(u["name"])
            users.append({"name": u["name"], **{k: a[k] for k in ("fails", "locks", "until", "blocked")}})
        return {"policy": asdict(svc.policy), "users": users, "factors": list(FACTORS), "now": svc.clock(),
                "states": [s.value for s in State], "transitions": [[a.value, e, d.value] for (a, e), d in TRANSITIONS.items()]}
    if path == "/api/policy" and m == "POST":
        svc.set_policy(b); return asdict(svc.policy)
    if path == "/api/users" and m == "POST":
        svc.add_user(b["name"], b["password"], b.get("phone", "")); return {"ok": True}
    if path == "/api/session" and m == "POST":
        return await (await svc.open(b["user"])).view()
    mm = re.fullmatch(r"/api/session/(\w+)(?:/(\w+))?", path)
    if mm:
        s, act = svc.sessions[mm[1]], mm[2]
        if act == "submit": await s.submit(b.get("answer", ""))
        elif act == "resend": await s.resend()
        elif act == "cancel": s.cancel()
        return await s.view()
    mm = re.fullmatch(r"/api/devices/(\w+)", path)
    if mm: return svc.devices(mm[1])
    mm = re.fullmatch(r"/api/unlock/(\w+)", path)
    if mm and m == "POST":
        svc.unlock(mm[1]); return {"ok": True}
    if path == "/api/audit": return svc.db.q("select * from audit order by id desc limit 100")
    raise FileNotFoundError(path)


def handler(svc):
    class H(BaseHTTPRequestHandler):
        def log_message(self, *a): pass
        def _send(self, code, body, ctype="application/json"):
            data = body if isinstance(body, bytes) else json.dumps(body).encode()
            self.send_response(code); self.send_header("Content-Type", ctype)
            self.send_header("Content-Length", str(len(data))); self.end_headers(); self.wfile.write(data)
        def _go(self, m):
            path = self.path.split("?")[0]
            if not path.startswith("/api/"):
                f = ROOT / "index.html" if path == "/" else WEB / path.lstrip("/")
                allowed = path == "/" or f.resolve().is_relative_to(WEB.resolve())
                if m != "GET" or not allowed or not f.is_file():
                    return self._send(404, {"error": "not found"})
                return self._send(200, f.read_bytes(), mimetypes.guess_type(f.name)[0] or "text/plain")
            try:
                body = json.loads(self.rfile.read(int(self.headers.get("Content-Length") or 0)) or "{}")
                code, out = 200, asyncio.run_coroutine_threadsafe(api(svc, m, path, body), LOOP).result(60)
            except InvalidTransition as e: code, out = 409, {"error": str(e)}
            except FileNotFoundError: code, out = 404, {"error": "not found"}
            except (ValueError, KeyError, TypeError, IndexError, sqlite3.IntegrityError) as e:
                code, out = 400, {"error": f"{type(e).__name__}: {e}"}
            self._send(code, out)
        def do_GET(self): self._go("GET")
        def do_POST(self): self._go("POST")
    return H


if __name__ == "__main__":
    ap = argparse.ArgumentParser()
    ap.add_argument("--port", type=int, default=8000)
    ap.add_argument("--db", default="mfa.db")
    ap.add_argument("--latency", type=float, default=0.8, help="simulated SMS delivery delay (s)")
    a = ap.parse_args()
    svc = Service(DB(a.db), latency=a.latency)
    if not svc.db.q("select 1 from users"):
        svc.add_user("alice", "Wonder#2026", "+91 98765 43210")
        svc.add_user("bob", "Builder#2026", "+91 91234 56789")
    print(f"MFA lab running at http://127.0.0.1:{a.port}  (Ctrl+C to stop)")
    ThreadingHTTPServer(("127.0.0.1", a.port), handler(svc)).serve_forever()
