# Run it in n8n

[`n8n/ai-call-prep-agent.json`](../n8n/ai-call-prep-agent.json) is the same agent for n8n. You enter a meeting in a form, and the brief lands in a Data table a couple of minutes later.

## What runs

1. **Meeting booked** (form): title, start, agenda, and one attendee per line as `Name, email, Company`.
2. **Attendees** (Code): drops your colleagues (your domain) and builds one Sales Navigator search per attendee: the name as keywords, the company as current company.
3. **Look up each attendee** (Evaboot MCP): an export of 1 person per search, with the verified email. 1 credit each.
4. **Export the buyers** (Evaboot MCP): the company's people with your buyer titles, up to `max_buyers`. 1 credit each.
5. **Facts** (Code): the same facts as `prep.py`: tenure from years and months together, the account's size, growth and teams, the buyers not on the invite.
6. **Write the notes** (Claude): the goal, talking points, questions and watch-outs, from the facts only.
7. **Check and render** (Code): flags any number that is not in the facts, then writes the one-page brief.
8. **Add to Call briefs** (Data table): one row per meeting.

## Set it up

1. **Import** the JSON in n8n: *Workflows > Import from file*.
2. **Add two credentials:**
   - **Bearer Auth** named `Evaboot MCP (Bearer)`: your key from [dash.evaboot.com/dash/api/](https://dash.evaboot.com/dash/api/). Select it on the four Evaboot nodes.
   - **Anthropic** on the **Claude** node.
3. **Make the Data table** *Call briefs* with the text columns `meeting`, `start`, `company`, `attendees`, `brief`.
4. **Fill in Your settings:** `your_domain`, `offer`, `buyer_titles` and `max_buyers` (0 to 5).
5. **Test:** open the form URL of **Meeting booked**, enter a real upcoming meeting, and wait for the row.

## Run it from your calendar

Replace **Meeting booked** with a **Google Calendar Trigger** (*Event Created*) or your booking tool's trigger (Calendly, Cal.com), and map the event title, start and attendees into the same three fields. Replace **Add to Call briefs** with a Gmail or Slack node to send the brief to yourself.

## Good to know

- The workflow waits 45 seconds for each export. If an export is still running, the run fails at **Facts**: run it again.
- An attendee whose name does not match in Sales Navigator is listed under "Not found". Add their company or fix the spelling.
- Claude retries up to 3 times: it sometimes returns an empty answer.

Back to the [README](../README.md).
