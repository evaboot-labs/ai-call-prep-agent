"""Builds n8n/ai-call-prep-agent.json. Run: python3 n8n/build_workflow.py

A form takes the meeting (or swap it for a calendar trigger, see docs/n8n.md). Evaboot looks up each
external attendee and the buyers not on the invite in Sales Navigator, a Code node turns the exports into
the same facts as prep.py, Claude writes the notes from those facts only, and the brief lands in the
"Call briefs" Data table.
"""
import json
import uuid
from pathlib import Path

MCP = "https://mcp.evaboot.com/mcp"
EVABOOT_CRED = {"httpBearerAuth": {"id": "", "name": "Evaboot MCP (Bearer)"}}
ANTHROPIC_CRED = {"anthropicApi": {"id": "", "name": "Anthropic"}}
MODEL = "claude-sonnet-5-5"

nodes, connections = [], {}


def node(name, type_, version, params, pos, creds=None, **extra):
    n = {"parameters": params, "id": str(uuid.uuid4()), "name": name, "type": type_,
         "typeVersion": version, "position": pos, **extra}
    if creds:
        n["credentials"] = creds
    nodes.append(n)


def link(a, b, kind="main", out=0):
    connections.setdefault(a, {}).setdefault(kind, [])
    while len(connections[a][kind]) <= out:
        connections[a][kind].append([])
    connections[a][kind][out].append({"node": b, "type": kind, "index": 0})


def code(name, js, pos, **extra):
    node(name, "n8n-nodes-base.code", 2, {"jsCode": js}, pos, **extra)


def mcp(name, tool, json_expr, pos):
    node(name, "@n8n/n8n-nodes-langchain.mcpClient", 1.1, {
        "endpointUrl": MCP, "authentication": "bearerAuth",
        "tool": {"__rl": True, "mode": "list", "value": tool, "cachedResultName": tool},
        "inputMode": "json", "jsonInput": json_expr, "options": {"timeout": 120000},
    }, pos, EVABOOT_CRED)


def wait(name, seconds, pos):
    node(name, "n8n-nodes-base.wait", 1.1, {"amount": seconds}, pos, webhookId=str(uuid.uuid4()))


SETTINGS = [
    ("your_domain", "evaboot.com"),
    ("offer", "An Evaboot plan: clean B2B leads with verified emails, exported from LinkedIn Sales Navigator."),
    ("buyer_titles", "VP Sales, Head of Sales, Sales Director, Chief Revenue Officer, Head of Business Development, "
                     "Revenue Operations, Sales Operations"),
    ("max_buyers", "5"),
]

# The MCP Client returns the tool result as text content; unwrap it to the tool's JSON.
UNWRAP = """
function unwrap(j) {
  let d = j && j.structuredContent ? j.structuredContent : j;
  if (d && Array.isArray(d.content) && d.content[0]) {
    const t = d.content[0].text;
    d = typeof t === 'string' ? JSON.parse(t) : t;
  }
  return d && d.result !== undefined ? d.result : d;
}
const SN = 'https://www.linkedin.com/sales/search/people?query=';
const enc = s => encodeURIComponent(s).replace(/[()']/g, c => '%' + c.charCodeAt(0).toString(16).toUpperCase());
const filter = (kind, vals) => `(type:${kind},values:List(${vals.map(v => `(text:${enc(v)},selectionType:INCLUDED)`).join(',')}))`;
const norm = s => (s || '').normalize('NFD').replace(/[\\u0300-\\u036f]/g, '').toLowerCase().replace(/[^a-z]/g, '');
"""

ATTENDEES_JS = UNWRAP + """
const s = $('Your settings').first().json;
const f = $('Meeting booked').first().json;
const mine = s.your_domain.toLowerCase();
const out = [];
for (const line of String(f.Attendees || '').split('\\n')) {
  const [name, email, company] = line.split(',').map(x => (x || '').trim());
  if (!name) continue;
  const domain = (email || '').toLowerCase().split('@')[1] || '';
  if (domain === mine) continue;
  const comp = company || (domain ? domain.split('.')[0] : '');
  if (!comp) continue;
  out.push({ json: { name, email, company: comp,
    search_url: `${SN}(keywords:${enc(name)},filters:List(${filter('CURRENT_COMPANY', [comp])}))` } });
}
if (!out.length) throw new Error('No external attendee: write one per line as Name, email, Company');
return out;
"""

COMMITTEE_JS = UNWRAP + """
const s = $('Your settings').first().json;
const rows = $input.all().flatMap(i => (unwrap(i.json) || {}).prospects || []);
const company = rows.length ? rows[0]['Company Name'] : $('Attendees').first().json.company;
const titles = s.buyer_titles.split(',').map(t => t.trim()).filter(Boolean);
return [{ json: { company, rows,
  search_url: `${SN}(filters:List(${filter('CURRENT_COMPANY', [company])},${filter('CURRENT_TITLE', titles)}))` } }];
"""

FACTS_JS = UNWRAP + """
const f = $('Meeting booked').first().json;
const att = $('Attendees').all().map(i => i.json);
const found = $('Account and buyers').first().json.rows;
const committee = (unwrap($input.first().json) || {}).prospects || [];
const tenure = (y, m) => { y = +y || 0; m = +m || 0;
  return [y ? `${y} ${y === 1 ? 'yr' : 'yrs'}` : '', (m || !y) ? `${m} mo` : ''].filter(Boolean).join(' '); };
const pretty = n => n.split(' ').map(w => w.length > 2 && w === w.toUpperCase() ? w[0] + w.slice(1).toLowerCase() : w).join(' ');
const cid = p => (p['Company Linkedin URL Unique ID'] || '').replace(/\\/$/, '').split('/').pop();
const person = p => ({
  name: pretty(p['Full Name'] || ''), title: p['Current Job'], headline: p['Profile Headline'], location: p['Location'],
  in_role: tenure(p['Years in Position'], p['Months in Position']),
  at_company: tenure(p['Years in Company'], p['Months in Company']),
  posts_30_days: p['Profile Recent Posts (30 Days)'], email: p['Email'], email_status: p['Email Status'],
  linkedin: p['Linkedin URL Public'], summary: (p['Profile Summary'] || '').slice(0, 400) });
const attendees = [], unmatched = [];
for (const a of att) {
  const hit = found.find(p => norm(p['Full Name']) === norm(a.name));
  if (hit) attendees.push(person(hit)); else unmatched.push(a.name);
}
const base = found.find(p => norm(p['Full Name']) === norm(attendees[0] && attendees[0].name)) || committee[0] || {};
const seen = new Set(attendees.map(p => norm(p.name)));
const not_on_invite = committee.filter(p => !seen.has(norm(p['Full Name'])) && (!base['Company Name'] || cid(p) === cid(base)))
  .map(p => { const x = person(p); return { name: x.name, title: x.title, in_role: x.in_role, email: x.email }; });
const depts = (base['Department Headcounts'] || '').split('\\n').map(l => l.split(':')).filter(x => x[1])
  .map(([k, v]) => [k.trim(), +v]).sort((a, b) => b[1] - a[1]).slice(0, 5).map(([k, v]) => `${k} ${v}`);
const account = { name: base['Company Name'], domain: base['Company Domain'], industry: base['Company Industry'],
  founded: base['Company Year Founded'], hq: base['Company Location'], employees: base['Company Employee Exact Count'],
  growth_6m_pct: base['Company Employee Growth 6 Months (%)'], growth_1y_pct: base['Company Employee Growth 1 Year (%)'],
  growth_2y_pct: base['Company Employee Growth 2 Years (%)'], sales_team: base['Sales Team Size'],
  business_development: base['Business Development Size'], top_departments: depts,
  description: base['Company Description'] };
return [{ json: { meeting: { title: f['Meeting title'], start: f['Start'], agenda: f['Agenda'] || '' },
  account, attendees, unmatched, not_on_invite } }];
"""

NOTES_PROMPT = """You prepare a sales rep for a booked call. Use only the facts in the JSON below: never add a fact from memory.
Write tenure exactly as given ("1 yr 3 mo"). Do not guess anyone's gender.

What we sell: {{ $('Your settings').first().json.offer }}

Return:
- goal: one sentence, what the rep wants out of this call.
- talking_points: 2 to 4. Each starts from one fact (time in role, a past company in a summary, the sales team size, growth, a buyer not on the invite) and says what to do with it.
- questions: 2 to 4 questions the facts cannot answer.
- watch_outs: 0 to 2, for example a very new attendee or flat growth.

Facts:
{{ JSON.stringify($json) }}"""

RENDER_JS = """
const f = $('Facts').first().json;
const n = $input.first().json.output || $input.first().json;
const nums = s => new Set((String(s).match(/\\d[\\d,]*(?:\\.\\d+)?/g) || []).map(x => x.replace(/,/g, '')));
const known = nums(JSON.stringify(f));
const unchecked = [...(n.talking_points || []), ...(n.questions || []), ...(n.watch_outs || [])]
  .filter(l => [...nums(l)].some(x => !known.has(x)));
const a = f.account || {};
const L = [`# Call prep: ${f.meeting.title}`, '', `**When:** ${f.meeting.start}`, '', `**Goal of the call:** ${n.goal}`, '',
  '## The account', '', `**${a.name}** (${a.domain}) · ${a.industry} · founded ${a.founded} · ${a.hq}`, '',
  `- ${a.employees} employees, ${a.growth_6m_pct}% in 6 months, ${a.growth_1y_pct}% in 1 year, ${a.growth_2y_pct}% in 2 years`,
  `- Sales team ${a.sales_team}, business development ${a.business_development}`,
  `- Biggest teams: ${(a.top_departments || []).join(', ')}`, '', '## Who you meet', '',
  '| Attendee | Role | In role | At company |', '|---|---|---|---|',
  ...f.attendees.map(p => `| ${p.name} | ${p.title} | ${p.in_role} | ${p.at_company} |`)];
if (f.unmatched.length) L.push('', `Not found in Sales Navigator: ${f.unmatched.join(', ')}.`);
if (f.not_on_invite.length) L.push('', '## Not on the invite', '', ...f.not_on_invite.map(p => `- ${p.name}, ${p.title} (${p.in_role} in role)`));
L.push('', '## Talking points', '', ...(n.talking_points || []).map((t, i) => `${i + 1}. ${t}`));
L.push('', '## Questions to ask', '', ...(n.questions || []).map((t, i) => `${i + 1}. ${t}`));
if ((n.watch_outs || []).length) L.push('', '## Watch out', '', ...n.watch_outs.map(t => `- ${t}`));
if (unchecked.length) L.push('', '## Check before the call', '', ...unchecked.map(t => `- A number here is not in the facts: ${t}`));
return [{ json: { meeting: f.meeting.title, start: f.meeting.start, company: a.name || '',
  attendees: f.attendees.map(p => p.name).join(', '), brief: L.join('\\n') } }];
"""

node("Meeting booked", "n8n-nodes-base.formTrigger", 2.2, {
    "formTitle": "Prepare a sales call",
    "formDescription": "One attendee per line: Name, email, Company",
    "formFields": {"values": [
        {"fieldLabel": "Meeting title", "requiredField": True},
        {"fieldLabel": "Start", "placeholder": "2026-11-04 10:00 CET", "requiredField": True},
        {"fieldLabel": "Agenda"},
        {"fieldLabel": "Attendees", "fieldType": "textarea", "requiredField": True,
         "placeholder": "Jane Doe, jane@acme.com, Acme"},
    ]},
    "options": {},
}, [0, 0], webhookId=str(uuid.uuid4()))
node("Your settings", "n8n-nodes-base.set", 3.4, {"assignments": {"assignments": [
    {"id": str(uuid.uuid4()), "name": k, "type": "string", "value": v} for k, v in SETTINGS]},
    "includeOtherFields": True, "options": {}}, [220, 0])
code("Attendees", ATTENDEES_JS, [440, 0], executeOnce=True)
mcp("Look up each attendee", "export_sn_search_or_list",
    "={{ JSON.stringify({ search_url: $json.search_url, name: 'call prep: ' + $json.name, max_results: 1 }) }}", [660, 0])
wait("Wait for the exports", 45, [880, 0])
mcp("Get the attendees", "get_export",
    "={{ JSON.stringify({ extraction_id: (j => { let d = j.structuredContent || j; if (d.content) d = JSON.parse(d.content[0].text); "
    "return (d.result || d).extraction_id; })($('Look up each attendee').item.json) }) }}", [1100, 0])
code("Account and buyers", COMMITTEE_JS, [0, 300])
mcp("Export the buyers", "export_sn_search_or_list",
    "={{ JSON.stringify({ search_url: $json.search_url, name: 'call prep: buyers at ' + $json.company, "
    "max_results: Number($('Your settings').first().json.max_buyers) }) }}", [220, 300])
wait("Wait for the buyers", 45, [440, 300])
mcp("Get the buyers", "get_export",
    "={{ JSON.stringify({ extraction_id: (j => { let d = j.structuredContent || j; if (d.content) d = JSON.parse(d.content[0].text); "
    "return (d.result || d).extraction_id; })($('Export the buyers').first().json) }) }}", [660, 300])
code("Facts", FACTS_JS, [880, 300])
node("Write the notes", "@n8n/n8n-nodes-langchain.chainLlm", 1.7, {
    "promptType": "define", "text": "=" + NOTES_PROMPT, "hasOutputParser": True,
}, [1100, 300], retryOnFail=True, maxTries=3, waitBetweenTries=2000)
node("Claude", "@n8n/n8n-nodes-langchain.lmChatAnthropic", 1.3, {
    "model": {"__rl": True, "mode": "list", "value": MODEL, "cachedResultName": MODEL},
    "options": {"maxTokensToSample": 3000},
}, [1060, 520], ANTHROPIC_CRED)
node("Notes", "@n8n/n8n-nodes-langchain.outputParserStructured", 1.3, {
    "schemaType": "manual",
    "inputSchema": json.dumps({"type": "object", "required": ["goal", "talking_points", "questions"], "properties": {
        "goal": {"type": "string"},
        "talking_points": {"type": "array", "items": {"type": "string"}},
        "questions": {"type": "array", "items": {"type": "string"}},
        "watch_outs": {"type": "array", "items": {"type": "string"}}}}, indent=2),
}, [1220, 520])
code("Check and render", RENDER_JS, [1400, 300])
node("Add to Call briefs", "n8n-nodes-base.dataTable", 1, {
    "dataTableId": {"__rl": True, "mode": "name", "value": "Call briefs"},
    "columns": {"mappingMode": "autoMapInputData", "value": {}, "matchingColumns": [], "schema": []},
    "options": {},
}, [1620, 300])

chain = ["Meeting booked", "Your settings", "Attendees", "Look up each attendee", "Wait for the exports",
         "Get the attendees", "Account and buyers", "Export the buyers", "Wait for the buyers", "Get the buyers",
         "Facts", "Write the notes", "Check and render", "Add to Call briefs"]
for a, b in zip(chain, chain[1:]):
    link(a, b)
link("Claude", "Write the notes", "ai_languageModel")
link("Notes", "Write the notes", "ai_outputParser")

workflow = {"name": "AI call prep agent (Evaboot + Claude)", "nodes": nodes, "connections": connections,
            "settings": {"executionOrder": "v1"}, "pinData": {}}
out = Path(__file__).with_name("ai-call-prep-agent.json")
out.write_text(json.dumps(workflow, indent=2, ensure_ascii=False) + "\n")
print(out, len(nodes), "nodes")
