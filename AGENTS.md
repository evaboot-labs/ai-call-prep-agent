# Agent instructions

This repo is an AI call prep agent. Before a booked sales call, it looks up each attendee in LinkedIn Sales Navigator through Evaboot (role, time in role and at the company, verified email), pulls the account's size, growth and sales team, lists the buyers who are not on the invite, and writes a one-page brief with talking points and questions tied to those facts. The user runs the call. When the user asks for call prep, a meeting brief, or "who am I meeting tomorrow":

1. Follow the skill in `skills/ai-call-prep/SKILL.md` step by step.
2. Read `MEETING.md` for the user's domain, offer and buyer titles. If it says `Status: EXAMPLE`, ask the user and update it.
3. Use `prep.py` for the search URLs, the facts, the check and the brief. The Evaboot MCP server does the Sales Navigator work (`.mcp.json`).
4. If the user is not connected yet, follow `docs/connect-your-agent.md` with them.
5. To run it every morning, follow `docs/schedule.md`. If the user wants n8n instead, follow `docs/n8n.md` with them one step at a time: you cannot click inside n8n, so say exactly what to do and wait for their confirmation.

Exports cost 1 Evaboot credit per person. Confirm with the user before the first export of each meeting. Never contact the attendees. Never ask for or handle another tool's API key: the user connects those in the tool itself. Never commit `.env`, `data/` or `briefs/`: they hold real people's data.
