# box-sandbox

A live browser sandbox ([easi.run](https://easi.run)) that runs on GitHub Actions. A human can watch and take
over; an AI agent can drive it over HTTPS with a token. Logins can be saved as encrypted profiles.

> Last verified end to end: 22 Nov 2026, from a fresh sandbox, using only the steps below.

## Connect as an AI agent (3 steps)

You need:
1. **Outbound HTTPS** from wherever your code runs, to `barryralphh.github.io` and `*.trycloudflare.com`.
   Many chat sandboxes have no internet, or only an allow-list. If yours cannot reach those hosts, it cannot connect.
   Use one that can (Claude Code, a GitHub Actions runner, a normal VM, Composio's workbench, ...).
2. **The agent token** (starts with `easi_`). The owner gives it to you. Never commit it or paste it in a public place.
3. **The box's current address.** It changes every restart (about every 5.5 hours), so never hard-code it.

### Step 1: get the current address

```bash
curl -s "https://barryralphh.github.io/box-link/link.txt?t=$(date +%s)"
# -> https://something-random.trycloudflare.com
```

Use `link.txt`. Do not use `https://barryralphh.github.io/box-link/`: that page redirects with JavaScript, so
`curl` and most agents just get HTML. The `?t=` part skips the cache. After a restart the file updates in about a minute.

### Step 2: call the API with the token

Every request needs the header `Authorization: Bearer $BOX_AGENT_TOKEN`. Send `Content-Type: application/json` on POST.

```bash
BASE=$(curl -s "https://barryralphh.github.io/box-link/link.txt?t=$(date +%s)")
curl -s -H "Authorization: Bearer $BOX_AGENT_TOKEN" "$BASE/api/agent/tools"            # list the 20 tools
curl -s -H "Authorization: Bearer $BOX_AGENT_TOKEN" "$BASE/api/agent/saved-sessions"   # saved logins
curl -s -H "Authorization: Bearer $BOX_AGENT_TOKEN" "$BASE/api/agent/sessions"         # running sessions
```

### Step 3: open a browser and use it

```bash
# start a session (returns an id, a window list and a watch_url)
curl -s -X POST -H "Authorization: Bearer $BOX_AGENT_TOKEN" -H "Content-Type: application/json" \
  -d '{"url":"https://example.com"}' "$BASE/api/agent/sessions"

# call a tool inside it:  POST /api/agent/sessions/<id>/tools/<tool>   with the tool's arguments as JSON
curl -s -X POST -H "Authorization: Bearer $BOX_AGENT_TOKEN" -H "Content-Type: application/json" \
  -d '{"url":"https://en.wikipedia.org"}' "$BASE/api/agent/sessions/<id>/tools/navigate"
```

### Or use the ready-made client (Python, standard library only)

```bash
export BOX_AGENT_TOKEN=easi_...        # from the owner
python3 box_client.py url              # current address
python3 box_client.py tools            # list tools
python3 box_client.py saved            # saved logins
python3 box_client.py open https://example.com
python3 box_client.py call <session-id> navigate '{"url":"https://example.com"}'
```

It looks up the address itself and retries a few times on 502/503/504 or a dead address (the box restarting).

## Tools and what is known to work

`list_windows, get_window_state, click, type_text, press_key, hotkey, scroll, get_desktop_state, run_steps,
run_script, list_files, save_download, send_file, choose_files, request_person, wait_for_control, inspect_page,
navigate, run_javascript, close_window`

Tested on 22 Nov 2026:

| Tool | Result |
|---|---|
| `navigate` | Works, about 0.4 to 1.4 s per page. Only `url` is required. |
| `list_windows`, `get_window_state` | Work. Take `pid` and `window_id` from `list_windows`. |
| `press_key` (`key`, optional `modifiers`) | Works, about 0.1 s. Good for Ctrl+L, Enter, Page_Down, Home. |
| `type_text` | Works. It is typed all at once, `delay_ms` is ignored. |
| `scroll` | **Fails** by default ("background delivery is not available"), also with `delivery_mode: "foreground"`. Scroll with `press_key` `Page_Down` instead. |
| `inspect_page` | Returned 502 every time. Avoid it for now. |

Tool inputs are listed by `GET /api/agent/tools` (each has a JSON schema).

## Things that will trip you up

- **The address changes.** Always fetch `link.txt` again after any failure. A restart takes about 2 to 3 minutes. DNS errors
  ("Name or service not known") or 502s usually mean the box is restarting or down.
- **Saved logins are locked after each restart.** `GET /api/agent/saved-sessions` shows `"unlocked": false` until the
  admin logs in on the admin page with their password. Until then an agent cannot use saved profiles.
- **The token only creates and drives sessions.** It cannot log into the admin page. The admin password and the
  authenticator code stay with the owner.
- **MCP works too.** The endpoint is `<address>/mcp` (address from `link.txt`), with the same Bearer token. Tested on 22 Nov 2026: it needs the headers `MCP-Protocol-Version: 2025-06-18` and `Accept: application/json, text/event-stream`. Protocol versions 2025-06-18, 2025-11-25 and 2026-07-28 are supported, an older version such as 2025-03-26 gets a 400. It is stateless (no session id). `tools/list` returns 26 tools: the 20 above plus `start_session`, `stop_session`, `list_sessions`, `list_saved_sessions`, `session_status` and `call_status`. Desktop tools take the session id as `session` and their own arguments under `arguments`. Because the address changes every restart, a client configured once breaks after a restart, so re-read `link.txt` or use `box_client.py` for the REST API.
  and the address changes, so a client configured once will break after a restart.
- **Be gentle:** automated posting and logins on Instagram or YouTube can get new accounts flagged. Start slow.

## How it works

| Piece | Where | What it does |
|---|---|---|
| `box.yml` | this repo | Installs easi.run on a runner, opens a Cloudflare quick tunnel, runs about 5.5 hours, then queues its own next run |
| `watchdog.yml` | this repo | Backup: starts the box if none is running (GitHub's cron is unreliable, so this is not relied on) |
| `box-state` | private repo | Encrypted backup of easi.run's `admin-state` volume every 5 minutes, restored at startup. Also holds the current address on the `link` branch |
| `box-link` | public repo + GitHub Pages | `link.txt` with the current address, rewritten at every start |

Secrets used: `BOX_STATE_SSH`, `BOX_STATE_KEY`, `BOX_LINK_SSH`, `NTFY_TOPIC` (and `BOX_AGENT_TOKEN` for workflows that
call the box). The ones named `*_SSH` are deploy keys limited to a single repository each.

## Notes for anyone editing the workflow

- Do not overwrite `box.yml` without testing a restart first. On 22 Nov 2026 a cache-based version (`bf71250d`) replaced the
  tested one. Its first restart failed (the admin kept retrying cleanup and the tunnel returned 502), and the box was down
  for about two hours until commit `9405f67` restored the working version.
- Test any change by cancelling the running box and dispatching `box.yml`, then check that the login screen appears
  (not the create-password screen) and that `box_client.py tools` works.

## Troubleshooting

| What you see | Likely cause | What to do |
|---|---|---|
| A DNS error or a 502 | The box is restarting or down, or your environment blocks trycloudflare.com | Wait 3 minutes and fetch link.txt again. If it still fails, check that your environment can open any other site |
| `401` | Wrong or revoked token | Ask the owner for a new one |
| `link.txt` returns an old address | Cached | Add `?t=<timestamp>`, and allow about a minute after a restart |
| Cannot reach github.io either | No internet in your environment | Use an environment with outbound HTTPS |
| `"unlocked": false` | Admin has not logged in since the restart | Ask the owner to log in |
