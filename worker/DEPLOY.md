# Worker: a fixed address for the box

`worker.js` is a Cloudflare Worker (free plan is enough). It gives the box one permanent URL:

- `https://<worker>.workers.dev/` sends a person to the box's current admin page.
- `https://<worker>.workers.dev/<PATH_KEY>/mcp` is the MCP endpoint, for connectors.
- `https://<worker>.workers.dev/<PATH_KEY>/api/agent/...` is the REST API.

It reads the box's current address from `link.txt` (see box-link), adds the agent token itself, and fixes the MCP
protocol-version header. Nothing secret is in this file. Two secrets are set in Cloudflare:

| Name | What |
|---|---|
| `BOX_TOKEN` | The easi.run agent token (starts with `easi_`) |
| `PATH_KEY` | A long random string. It becomes part of the URL, so treat the whole URL as a password |

Deploy: Cloudflare dashboard, Workers and Pages, Create, Start with Hello World, Deploy, Edit code, paste `worker.js`,
Deploy. Then Settings, Variables and Secrets, add the two secrets as type Secret, and Deploy again.

Tested on 22 Nov 2026 in Node against the live box: root redirect, wrong key rejected, admin path blocked,
MCP initialize, MCP tools/list without a version header (26 tools), REST tools (20).
