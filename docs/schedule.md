# Get a brief every morning

Run the agent once a day on the next day's meetings, so every brief is ready before you open your calendar.

1. **Connect your calendar** to Claude: *Settings > Connectors*, then Google Calendar or Outlook. Connect Evaboot the same way (`https://mcp.evaboot.com/mcp`, see [connect-your-agent.md](connect-your-agent.md)).
2. **Create the task.** In Claude, a scheduled task, or in Claude Code a routine, every weekday at 7:00, with this prompt:

   ```text
   Read my calendar for tomorrow. For each meeting with at least one attendee outside <your domain>,
   follow the skill in https://github.com/evaboot-labs/ai-call-prep-agent (skills/ai-call-prep/SKILL.md):
   look up the attendees and up to 5 buyers not on the invite with Evaboot, write the brief from those
   facts only, and send me all briefs in one message. Skip internal meetings. Spend at most 30 credits a day.
   ```
3. **Run it once by hand** and read the first briefs before you leave it on.

Each meeting costs 1 credit per external attendee plus up to 5 for the buyers not on the invite. A day with no external meeting costs nothing.

Back to the [README](../README.md).
