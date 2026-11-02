---
name: ai-call-prep
description: Prepare a one-page brief before a booked sales call - look up each external attendee in LinkedIn Sales Navigator with Evaboot (role, time in role and at the company, verified email), pull the account's size, growth and sales team, list the buyers who are not on the invite, then write talking points and questions tied to those facts only. Use when the user has a meeting, demo or discovery call coming up and asks for call prep, a meeting brief, account research before a call, or "who am I meeting tomorrow".
---

# AI call prep

This skill runs inside a clone of https://github.com/evaboot-labs/ai-call-prep-agent: it uses the repo's `prep.py`, `MEETING.md` and `docs/`. If `prep.py` is not in the working directory, clone the repo and work from there.

The Sales Navigator and Evaboot work goes through the Evaboot MCP server (`https://mcp.evaboot.com/mcp`); every tool named below is an Evaboot MCP tool. `prep.py` makes no network calls: it builds the search URLs, matches the attendees, turns the exports into facts, checks your notes and renders the brief.

## Rules

- Exports cost 1 Evaboot credit per person. One call costs about 2 to 8 credits: 1 per attendee, plus up to 5 for the buyers not on the invite. Say the cost and wait for a yes before the first export of each meeting.
- Write the notes only from `data/facts.json`. Never add a fact from memory or the web. If a fact is missing, write the question instead.
- Read tenure from both fields: Evaboot splits it into years and months (`Years in Position` + `Months in Position`). `prep.py facts` already joins them; never quote the months alone.
- Never send anything to the attendees. The brief is for the user.
- Print every Sales Navigator URL as a Markdown link with the URL in angle brackets: `[Open in Sales Navigator](<url>)`.

## Step 0: check the setup

1. If the Evaboot MCP tools are not in this session, the user is not connected yet. Walk them through `docs/connect-your-agent.md`, then ask them to restart the agent from this folder.
2. Otherwise call `get_daily_export_quota`. `has_valid_salesnav` must be true. If not, send the user to `docs/connect-your-agent.md`, step 1.
3. Run `mkdir -p data/attendees briefs`. Both folders are git-ignored: they hold real people's data.
4. Read `MEETING.md`. If it says `Status: EXAMPLE`, ask the user for their domain, what they sell, their buyer titles and the call type. Update the file and remove the status line.

## Step 1: get the meeting

1. If the session has a calendar tool (Google Calendar, Outlook), read the meetings the user names, or tomorrow's meetings with at least one attendee outside their domain. Otherwise ask the user to paste the invite: title, time, attendees with emails.
2. Write it to `data/invite.json`: `title`, `start`, `agenda`, `booked_by` and `attendees` (a list of `name`, `email`, and `company` when you know it). The company is the name behind the email domain: `agicap.com` is Agicap. Ask when you are not sure.
3. Run `python3 prep.py invite data/invite.json`. It drops the user's own colleagues and prints one `lookup_url` per external attendee. A `note` means a personal email or a missing company: ask the user.

## Step 2: look up the attendees

For each external attendee, call `export_sn_search_or_list` with the `lookup_url`, `max_results: 1` and a name like `call prep: <name>`. Poll `get_export` until the status is `EXECUTED`, then save the whole result to `data/attendees/<first-name>.json`.

If an export returns 0 people, the name or company did not match. Ask the user for the attendee's LinkedIn URL and call `export_profile` with it instead. Save the result the same way.

## Step 3: the buyers not on the invite

1. Run `python3 prep.py committee-url "<company>"`. It searches the company for the buyer titles in `MEETING.md`.
2. Call `export_sn_search_or_list` with that URL and `max_results: 5`. Save the result to `data/committee.json`.
3. Skip this step when the user says the attendees are the only people who decide.

## Step 4: facts

```bash
python3 prep.py facts data/invite.json data/attendees/*.json --committee data/committee.json > data/facts.json
```

Read `unmatched` and the stderr line: those attendees had no match by name. Tell the user. The committee keeps only people whose LinkedIn company id is the attendees' company: a text company filter also matches look-alike pages.

## Step 5: write the notes

Read `data/facts.json` in full, including each `summary` and the account `description`. Write `data/notes.json`:

- `goal`: one sentence, what the user wants out of this call.
- `talking_points`: 2 to 4. Each one starts from one fact (time in role, a past company in the summary, the sales team size, growth, a buyer not on the invite) and says what to do with it.
- `questions`: 2 to 4 questions the facts cannot answer.
- `watch_outs`: 0 to 2, for example a very new attendee or flat growth.

Then:

```bash
python3 prep.py check data/facts.json data/notes.json
python3 prep.py render data/facts.json data/notes.json > briefs/<date>-<company>.md
```

`check` fails when a number in the notes is not in the facts. Fix the note, never the facts.

## Step 6: deliver

Show the user the brief and the file path. If they want it somewhere else, put it there with the tools the session has: a Google Doc, a note on the CRM deal, an email draft to themselves. Ask before you save it anywhere outside this folder.

To run this every morning for the next day's meetings, follow `docs/schedule.md`.
