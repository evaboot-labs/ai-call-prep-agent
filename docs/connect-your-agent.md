# Connect your AI Agent by hand

The prompt in the README does all of this for you. These are the same steps, for when you want to do them yourself.

1. **Create your Evaboot account** at [dash.evaboot.com](https://dash.evaboot.com/accounts/signup/?last_click_origin=ai-call-prep-agent-repo) and install the [Chrome extension](https://dash.evaboot.com/install/) to connect Sales Navigator. You need an active Sales Navigator seat.
2. **Get the repo:**
   ```bash
   git clone https://github.com/evaboot-labs/ai-call-prep-agent.git
   cd ai-call-prep-agent
   ```
3. **Connect the Evaboot MCP server.** Copy your API key from [dash.evaboot.com/dash/api/](https://dash.evaboot.com/dash/api/), then:
   ```bash
   cp .env.example .env          # paste the key after EVABOOT_API_KEY=
   export EVABOOT_API_KEY=...    # same key, for your agent
   ```
   - **Claude Code** reads `.mcp.json` in this folder and uses `EVABOOT_API_KEY` from your environment. Export the key before you start Claude Code.
   - **Codex:** `codex mcp add evaboot --url https://mcp.evaboot.com/mcp --bearer-token-env-var EVABOOT_API_KEY`
   - **Cursor:** add `https://mcp.evaboot.com/mcp` with the header `Authorization: Bearer <your key>`.
   - **Claude or ChatGPT on the web:** add `https://mcp.evaboot.com/mcp` as a custom connector and sign in.
4. **Optional: connect your calendar** (the Google Calendar or Outlook connector of your agent), so it reads your meetings instead of asking you to paste them.
5. **Say what you sell** in [`MEETING.md`](../MEETING.md), or let your agent ask you.
6. **Check** (Python 3.9+, no packages to install):
   ```bash
   python3 prep.py committee-url "Acme"
   ```
   It prints a Sales Navigator URL.

Then ask your agent: **"Prepare my call with <attendees> at <company> tomorrow."**

Back to the [README](../README.md).
