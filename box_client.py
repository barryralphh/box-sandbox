#!/usr/bin/env python3
"""Tiny client for the box (easi.run agent API). Standard library only.

  export BOX_AGENT_TOKEN=...            # given to you by the owner, never commit it
  python3 box_client.py url             # print the box's current address
  python3 box_client.py tools           # list the browser tools
  python3 box_client.py saved           # list saved (logged-in) profiles
  python3 box_client.py sessions        # list running sessions
  python3 box_client.py open URL        # start a browser session on URL
  python3 box_client.py call SESSION TOOL '{"json": "args"}'
"""
import json, os, re, sys, time, urllib.request, urllib.error

LINK_URL = "https://barryralphh.github.io/box-link/link.txt"
UA = "box-client/1.0"


def get_base():
    req = urllib.request.Request(f"{LINK_URL}?t={int(time.time())}", headers={"User-Agent": UA})
    with urllib.request.urlopen(req, timeout=20) as r:
        base = r.read().decode().strip()
    if not re.fullmatch(r"https://[a-z0-9-]+\.trycloudflare\.com", base):
        raise SystemExit(f"unexpected address in link.txt: {base!r}")
    return base


def api(method, path, body=None, tries=4):
    token = os.environ.get("BOX_AGENT_TOKEN")
    if not token:
        raise SystemExit("set BOX_AGENT_TOKEN first")
    base = get_base()
    data = json.dumps(body).encode() if body is not None else None
    for i in range(tries):
        req = urllib.request.Request(
            base + path, data=data, method=method,
            headers={"Authorization": "Bearer " + token, "Content-Type": "application/json", "User-Agent": UA})
        try:
            with urllib.request.urlopen(req, timeout=120) as r:
                return json.loads(r.read().decode() or "{}")
        except urllib.error.HTTPError as e:
            if e.code in (502, 503, 504) and i < tries - 1:
                time.sleep(3 * (i + 1)); base = get_base(); continue
            raise SystemExit(f"HTTP {e.code} from {path}: {e.read().decode()[:300]}")
        except urllib.error.URLError as e:
            if i < tries - 1:
                time.sleep(3 * (i + 1)); base = get_base(); continue
            raise SystemExit(f"cannot reach the box: {e.reason}")


def main(argv):
    if not argv:
        print(__doc__); return
    cmd = argv[0]
    if cmd == "url":
        print(get_base())
    elif cmd == "tools":
        for t in api("GET", "/api/agent/tools")["tools"]:
            print(t["name"])
    elif cmd == "saved":
        print(json.dumps(api("GET", "/api/agent/saved-sessions"), indent=1))
    elif cmd == "sessions":
        print(json.dumps(api("GET", "/api/agent/sessions"), indent=1))
    elif cmd == "open":
        print(json.dumps(api("POST", "/api/agent/sessions", {"url": argv[1]}), indent=1))
    elif cmd == "call":
        args = json.loads(argv[3]) if len(argv) > 3 else {}
        print(json.dumps(api("POST", f"/api/agent/sessions/{argv[1]}/tools/{argv[2]}", args), indent=1))
    else:
        print(__doc__)


if __name__ == "__main__":
    main(sys.argv[1:])
