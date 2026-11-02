#!/usr/bin/env python3
"""Call prep helper. No network calls: the Evaboot MCP server does the Sales Navigator work.

  python3 prep.py invite data/invite.json                 external attendees + one lookup URL each
  python3 prep.py committee-url "Agicap"                  people search for the buyers not on the invite
  python3 prep.py facts data/invite.json data/attendees/*.json --committee data/committee.json > data/facts.json
  python3 prep.py check data/facts.json data/notes.json   every number in your notes must be in the facts
  python3 prep.py render data/facts.json data/notes.json > briefs/<date>-<company>.md

Python 3.9+, standard library only.
"""
import argparse
import json
import re
import sys
from pathlib import Path
from urllib.parse import quote

ROOT = Path(__file__).parent
SN = "https://www.linkedin.com/sales/search/people?query="
FREE_MAIL = {"gmail.com", "googlemail.com", "outlook.com", "hotmail.com", "yahoo.com", "icloud.com", "proton.me"}


def meeting_md():
    """Read the buyer titles and your own domain from MEETING.md."""
    text = (ROOT / "MEETING.md").read_text()
    titles = re.search(r"^Buyer titles:\s*(.+)$", text, re.M)
    domain = re.search(r"^Your domain:\s*(\S+)", text, re.M)
    return ([t.strip() for t in titles.group(1).split(",")] if titles else [],
            domain.group(1).lower() if domain else "")


def sn_filter(kind, values):
    vals = ",".join(f"(text:{quote(v, safe='')},selectionType:INCLUDED)" for v in values)
    return f"(type:{kind},values:List({vals}))"


def lookup_url(name, company):
    """People search: the attendee's name as keywords, the company as current company."""
    return f"{SN}(keywords:{quote(name, safe='')},filters:List({sn_filter('CURRENT_COMPANY', [company])}))"


def committee_url(company, titles):
    return f"{SN}(filters:List({sn_filter('CURRENT_COMPANY', [company])},{sn_filter('CURRENT_TITLE', titles)}))"


def norm(s):
    return re.sub(r"[^a-z]", "", (s or "").lower()
                  .translate(str.maketrans("àâäéèêëîïôöùûüçñ", "aaaeeeeiioouuucn")))


def prospects(path):
    d = json.loads(Path(path).read_text())
    if isinstance(d, dict) and "result" in d:
        d = d["result"]
    if isinstance(d, dict):
        d = d.get("prospects")
    if not isinstance(d, list):
        sys.exit(f"{path}: no 'prospects' list. Poll get_export until the status is EXECUTED and save that result.")
    return d


def tenure(years, months):
    """Evaboot splits tenure into years and months. Never read one without the other."""
    y, m = int(years or 0), int(months or 0)
    parts = [f"{y} yr" if y == 1 else f"{y} yrs"] if y else []
    if m or not y:
        parts.append(f"{m} mo")
    return " ".join(parts), y * 12 + m


def pretty(name):
    """LinkedIn names often come as 'Thomas CLOTTEAU': title-case the all-caps words."""
    return " ".join(w.title() if w.isupper() and len(w) > 2 else w for w in name.split())


def person(p):
    role, role_m = tenure(p.get("Years in Position"), p.get("Months in Position"))
    comp, comp_m = tenure(p.get("Years in Company"), p.get("Months in Company"))
    flags = [k.replace("Profile ", "").replace(" (90 Days)", "") for k in
             ("Profile Recently Promoted (90 Days)", "Profile Recently Hired (90 Days)") if p.get(k) == "Yes"]
    return {
        "name": pretty(p.get("Full Name") or f"{p.get('First Name', '')} {p.get('Last Name', '')}".strip()),
        "title": p.get("Current Job", ""),
        "headline": p.get("Profile Headline", ""),
        "location": p.get("Location", ""),
        "in_role": role, "in_role_months": role_m,
        "at_company": comp, "at_company_months": comp_m,
        "positions_on_profile": p.get("Total Positions Count", ""),
        "posts_30_days": p.get("Profile Recent Posts (30 Days)", ""),
        "flags": flags,
        "email": p.get("Email", ""), "email_status": p.get("Email Status", ""),
        "linkedin": p.get("Linkedin URL Public", ""),
        "sales_navigator": p.get("Sales Navigator URL", ""),
        "company_id": (p.get("Company Linkedin URL Unique ID") or "").rstrip("/").split("/")[-1],
        "summary": (p.get("Profile Summary") or "")[:400],
    }


def account(p):
    depts = {}
    for line in (p.get("Department Headcounts") or "").splitlines():
        k, _, v = line.partition(":")
        if v.strip().isdigit():
            depts[k.strip()] = int(v)
    top = sorted(depts.items(), key=lambda kv: -kv[1])[:5]
    rmin, rmax = p.get("Company Revenue Min (Millions USD)"), p.get("Company Revenue Max (Millions USD)")
    return {
        "name": p.get("Company Name", ""), "domain": p.get("Company Domain", ""),
        "linkedin_id": (p.get("Company Linkedin URL Unique ID") or "").rstrip("/").split("/")[-1],
        "industry": p.get("Company Industry", ""), "type": p.get("Company Type", ""),
        "founded": p.get("Company Year Founded", ""), "hq": p.get("Company Location", ""),
        "employees": p.get("Company Employee Exact Count", ""),
        "growth_6m_pct": p.get("Company Employee Growth 6 Months (%)", ""),
        "growth_1y_pct": p.get("Company Employee Growth 1 Year (%)", ""),
        "growth_2y_pct": p.get("Company Employee Growth 2 Years (%)", ""),
        "sales_team": p.get("Sales Team Size", ""), "business_development": p.get("Business Development Size", ""),
        "revenue_musd": f"{rmin}-{rmax}" if rmin and rmax else "",
        "top_departments": [f"{k} {v}" for k, v in top],
        "description": p.get("Company Description", ""),
    }


def cmd_invite(a):
    inv = json.loads(Path(a.invite).read_text())
    _, mine = meeting_md()
    out = []
    for att in inv.get("attendees", []):
        email = (att.get("email") or "").lower()
        domain = email.split("@")[-1] if "@" in email else ""
        if mine and domain == mine:
            continue
        company = att.get("company") or inv.get("company") or ""
        row = {"name": att.get("name", ""), "email": email, "company": company}
        if not company and domain and domain not in FREE_MAIL:
            row["note"] = f"no company given: ask the user, or use the name behind {domain}"
        if domain in FREE_MAIL:
            row["note"] = "personal email: ask the user for the company"
        if row["name"] and company:
            row["lookup_url"] = lookup_url(row["name"], company)
        out.append(row)
    print(json.dumps({"meeting": inv.get("title", ""), "start": inv.get("start", ""), "external": out},
                     indent=1, ensure_ascii=False))


def cmd_committee_url(a):
    titles, _ = meeting_md()
    if not titles:
        sys.exit("MEETING.md has no 'Buyer titles:' line")
    print(committee_url(a.company, titles))


def cmd_facts(a):
    inv = json.loads(Path(a.invite).read_text())
    _, mine = meeting_md()
    wanted = [x for x in inv.get("attendees", []) if not (mine and x.get("email", "").lower().endswith("@" + mine))]
    found, unmatched, acct = [], [], None
    rows = [p for f in a.attendee_exports for p in prospects(f)]
    for att in wanted:
        key = norm(att.get("name"))
        hit = next((p for p in rows if norm(p.get("Full Name") or p.get("First Name", "") + p.get("Last Name", "")) == key), None)
        if hit is None:
            unmatched.append(att.get("name"))
            continue
        acct = acct or account(hit)
        pp = person(hit)
        pp["invite_email"] = att.get("email", "")
        found.append(pp)
    others = []
    if a.committee:
        seen = {norm(p["name"]) for p in found}
        for p in prospects(a.committee):
            pp = person(p)
            if norm(pp["name"]) in seen:
                continue
            if acct and pp["company_id"] != acct["linkedin_id"]:
                continue  # a text company filter also matches look-alike pages
            acct = acct or account(p)
            others.append({k: pp[k] for k in ("name", "title", "location", "in_role", "email", "email_status", "linkedin")})
    print(json.dumps({"meeting": {k: inv.get(k, "") for k in ("title", "start", "booked_by", "agenda")},
                      "account": acct, "attendees": found, "unmatched": unmatched, "not_on_invite": others},
                     indent=1, ensure_ascii=False))
    if unmatched:
        print(f"no Sales Navigator match for: {', '.join(unmatched)}", file=sys.stderr)


def numbers(text):
    return {n.replace(",", "") for n in re.findall(r"\d[\d,]*(?:\.\d+)?", text or "")}


def values(x):
    """Only the values: digits in key names (growth_6m_pct) must not count as facts."""
    if isinstance(x, dict):
        return " ".join(values(v) for v in x.values())
    if isinstance(x, list):
        return " ".join(values(v) for v in x)
    return str(x)


def cmd_check(a):
    facts = json.loads(Path(a.facts).read_text())
    notes = json.loads(Path(a.notes).read_text())
    known = numbers(values(facts))
    bad = []
    for section in ("talking_points", "questions", "watch_outs"):
        for line in notes.get(section, []):
            miss = numbers(line) - known
            if miss:
                bad.append(f"{section}: {', '.join(sorted(miss))} not in the facts: {line}")
    for k in ("talking_points", "questions"):
        if not 2 <= len(notes.get(k, [])) <= 4:
            bad.append(f"{k}: write 2 to 4")
    print("\n".join(bad) or "ok")
    sys.exit(1 if bad else 0)


def cmd_render(a):
    f = json.loads(Path(a.facts).read_text())
    n = json.loads(Path(a.notes).read_text())
    m, ac = f["meeting"], f["account"] or {}
    out = [f"# Call prep: {m.get('title', '')}", "",
           f"**When:** {m.get('start', '')}" + (f" · **Agenda:** {m['agenda']}" if m.get("agenda") else ""), "",
           f"**Goal of the call:** {n.get('goal', '')}", "", "## The account", "",
           f"**{ac.get('name', '')}** ({ac.get('domain', '')}) · {ac.get('industry', '')} · founded {ac.get('founded', '')} · {ac.get('hq', '')}", "",
           f"- {ac.get('employees', '')} employees, {ac.get('growth_6m_pct', '')}% in 6 months, "
           f"{ac.get('growth_1y_pct', '')}% in 1 year, {ac.get('growth_2y_pct', '')}% in 2 years",
           f"- Sales team {ac.get('sales_team', '')}, business development {ac.get('business_development', '')}"
           + (f", revenue {ac['revenue_musd']} M USD (LinkedIn range)" if ac.get("revenue_musd") else ""),
           f"- Biggest teams: {', '.join(ac.get('top_departments', []))}", "", "## Who you meet", "",
           "| Attendee | Role | In role | At company | Notes |", "|---|---|---|---|---|"]
    for p in f["attendees"]:
        note = "; ".join(p["flags"] + ([f"{p['posts_30_days']} posts in 30 days"] if p["posts_30_days"] not in ("", "0") else []))
        out.append(f"| {p['name']} | {p['title']} | {p['in_role']} | {p['at_company']} | {note or '-'} |")
    if f.get("unmatched"):
        out.append(f"\nNot found in Sales Navigator: {', '.join(f['unmatched'])}.")
    if f.get("not_on_invite"):
        out += ["", "## Not on the invite", ""]
        out += [f"- {p['name']}, {p['title']} ({p['in_role']} in role)" for p in f["not_on_invite"]]
    out += ["", "## Talking points", ""] + [f"{i}. {t}" for i, t in enumerate(n.get("talking_points", []), 1)]
    out += ["", "## Questions to ask", ""] + [f"{i}. {t}" for i, t in enumerate(n.get("questions", []), 1)]
    if n.get("watch_outs"):
        out += ["", "## Watch out", ""] + [f"- {t}" for t in n["watch_outs"]]
    out += ["", "<sub>Facts from LinkedIn Sales Navigator via Evaboot. Notes written by your AI Agent from those facts only.</sub>"]
    print("\n".join(out))


def main():
    ap = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    sub = ap.add_subparsers(dest="cmd", required=True)
    s = sub.add_parser("invite"); s.add_argument("invite"); s.set_defaults(fn=cmd_invite)
    s = sub.add_parser("committee-url"); s.add_argument("company"); s.set_defaults(fn=cmd_committee_url)
    s = sub.add_parser("facts"); s.add_argument("invite"); s.add_argument("attendee_exports", nargs="+")
    s.add_argument("--committee"); s.set_defaults(fn=cmd_facts)
    s = sub.add_parser("check"); s.add_argument("facts"); s.add_argument("notes"); s.set_defaults(fn=cmd_check)
    s = sub.add_parser("render"); s.add_argument("facts"); s.add_argument("notes"); s.set_defaults(fn=cmd_render)
    a = ap.parse_args()
    a.fn(a)


if __name__ == "__main__":
    main()
