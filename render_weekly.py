#!/usr/bin/env python3
"""Self-contained renderer for D3's weekly KPI report (stdlib only).

Ported from /root/kpi-report/publish_weekly_gdoc.py. Produces byte-identical
table HTML, but reads data + narrative from JSON files instead of calling
weekly_report.build_weekly_data() / Drive. No third-party imports, no
dependency on the weekly_report module.

Run: python3 render_weekly.py <data.json> <narrative.json> > out.html
"""
import json
import math
import sys


def _trunc1(x):
    """Truncate toward zero to 1 decimal (Matt's convention: never round up)."""
    return math.floor(abs(x) * 10) / 10.0


# --- Inlined formatters (copies of weekly_report's, with None guards) ---------
def fmt_money_dollars(usd):
    if usd is None:
        return "—"
    if usd >= 1_000_000:
        return f"${_trunc1(usd / 1_000_000):.1f}M"
    if usd >= 1_000:
        return f"${_trunc1(usd / 1_000):.1f}K"
    return f"${int(usd)}"


def fmt_money_nav(usd):
    """NAV-only: 2-decimal truncation (Matt's documented exception to the 1-decimal
    money format). Ex 30977403 -> $30.97M."""
    if usd is None:
        return "—"
    if usd >= 1_000_000:
        return f"${math.floor(usd / 10_000) / 100:.2f}M"
    if usd >= 1_000:
        return f"${math.floor(usd / 10) / 100:.2f}K"
    return f"${int(usd)}"


def fmt_count(n):
    if n is None:
        return "—"
    return f"{int(round(n)):,}"


def fmt_pct(p):
    if p is None:
        return "  —"
    sign = "+" if p >= 0 else "-"
    return f"{sign}{_trunc1(p):.1f}%"


def _pct(p):
    return fmt_pct(p).strip()


def _goal(v, target, suffix):
    """Progress vs. goal. Reads 'X% to <goal>' under 100%, 'X% of <goal> goal'
    once the goal is met/exceeded (so an over-100% metric doesn't read as 'to')."""
    if v is None:
        return ""
    pct = int(v / target * 100)  # truncate toward zero
    if pct >= 100:
        return f"{pct}% of {suffix} goal"
    return f"{pct}% to {suffix}"


TH = 'style="border:1px solid #ccc;padding:5px 9px;background:#f3f3f3;text-align:%s;font-weight:bold"'
TD = 'style="border:1px solid #ccc;padding:5px 9px;text-align:%s"'


def _kpi_table(d):
    k = d["kpis"]; mv = k["monthly_volume"]; ta = k["tokenized_assets"]; bd = ta["breakdown"]
    mau = k["mau"]; lau = k["domain_launches"]; nav = k["nav"]
    money = fmt_money_dollars; cnt = fmt_count

    def row(label, this_wk, last_wk, wow, goal, indent=False):
        lbl = ("&nbsp;&nbsp;&nbsp;&nbsp;" + label) if indent else f"<b>{label}</b>"
        return (f"<tr><td {TD % 'left'}>{lbl}</td>"
                f"<td {TD % 'right'}>{this_wk}</td><td {TD % 'right'}>{last_wk}</td>"
                f"<td {TD % 'right'}>{_pct(wow)}</td><td {TD % 'left'}>{goal}</td></tr>")

    nav_goal = _goal(nav["last_end"], 30_000_000, "$30M")
    rows = [
        f"<tr>{''.join(f'<th {TH % a}>{h}</th>' for h,a in [('Metric','left'),('This wk','right'),('Last wk','right'),('WoW','right'),('Goal','left')])}</tr>",
        row("Monthly Volume", money(mv["headline_30d"]), money(mv["prior_30d_total"]), mv["rolling_30d_pct"], _goal(mv["headline_30d"], 100_000_000, "$100M/mo")),
        row("Network Asset Value", fmt_money_nav(nav["last_end"]), fmt_money_nav(nav["prior_end"]), nav["wow_pct"], nav_goal),
        row("MAU", cnt(mau["last_end"]), cnt(mau["prior_end"]), mau["wow_pct"], _goal(mau["last_end"], 20_000, "20K")),
        row("Total Domains Onchain", cnt(ta["last_end"]), cnt(ta["prior_end"]), ta["wow_pct"], _goal(ta["last_end"], 1_000_000, "1M")),
        row("domains", cnt(bd["domains"]["last_end"]), cnt(bd["domains"]["prior_end"]), bd["domains"]["wow_pct"], "", indent=True),
        row("subdomains", cnt(bd["subdomains"]["last_end"]), cnt(bd["subdomains"]["prior_end"]), bd["subdomains"]["wow_pct"], "", indent=True),
        row("name tokens", cnt(bd["name_tokens"]["last_end"]), cnt(bd["name_tokens"]["prior_end"]), bd["name_tokens"]["wow_pct"], "", indent=True),
        row("Fractional Launches", cnt(lau["last_end"]), cnt(lau["prior_end"]), lau["wow_pct"], _goal(lau["last_end"], 500, "500")),
    ]
    return '<table style="border-collapse:collapse;font-size:10pt">' + "".join(rows) + "</table>"


def _frac_table(d):
    """Graduation Rates table: rate per channel per period, plus a volume-weighted Total row."""
    gc = d["graduation_by_channel"]
    wg = gc.get("white_glove", {})
    ss = gc.get("self_serve", {})

    def rate(ch, per):
        r = gc.get(ch, {}).get(per, {}).get("rate")
        return f"{r:.0f}%" if r is not None else "&mdash;"

    def total_rate(per):
        wl = wg.get(per, {}).get("launches", 0)
        sl = ss.get(per, {}).get("launches", 0)
        wgr = wg.get(per, {}).get("graduated", 0)
        sgr = ss.get(per, {}).get("graduated", 0)
        tl = wl + sl
        return f"{100 * (wgr + sgr) / tl:.0f}%" if tl else "&mdash;"

    pers = ["q1", "q2", "l30", "all"]
    head = ['Graduation Rates', 'Q1', 'Q2', 'Trailing 30d', 'All time']
    rows = ["<tr>" + "".join(f"<th {TH % ('left' if i==0 else 'right')}>{h}</th>" for i,h in enumerate(head)) + "</tr>"]
    for label, ch in [("White glove", "white_glove"), ("Self serve", "self_serve")]:
        rows.append(f"<tr><td {TD % 'left'}>{label}</td>"
                    + "".join(f"<td {TD % 'right'}>{rate(ch, p)}</td>" for p in pers) + "</tr>")
    rows.append(f"<tr><td {TD % 'left'}><b>Total</b></td>"
                + "".join(f"<td {TD % 'right'}>{total_rate(p)}</td>" for p in pers) + "</tr>")
    return '<table style="border-collapse:collapse;font-size:10pt">' + "".join(rows) + "</table>"


def _frac_launch_table(d):
    """Launch Volume table: launches/graduations per channel for Q1 and Q2, plus a Total row."""
    gc = d["graduation_by_channel"]
    wg = gc.get("white_glove", {})
    ss = gc.get("self_serve", {})

    def cell(ch, per, key):
        return gc.get(ch, {}).get(per, {}).get(key, 0)

    head = ['Launch Volume', 'Q1 Launches', 'Q1 Graduations', 'Q2 Launches', 'Q2 Graduations']
    rows = ["<tr>" + "".join(f"<th {TH % ('left' if i==0 else 'right')}>{h}</th>" for i,h in enumerate(head)) + "</tr>"]
    for label, ch in [("White glove", "white_glove"), ("Self serve", "self_serve")]:
        rows.append(f"<tr><td {TD % 'left'}>{label}</td>"
                    f"<td {TD % 'right'}>{cell(ch,'q1','launches')}</td>"
                    f"<td {TD % 'right'}>{cell(ch,'q1','graduated')}</td>"
                    f"<td {TD % 'right'}>{cell(ch,'q2','launches')}</td>"
                    f"<td {TD % 'right'}>{cell(ch,'q2','graduated')}</td></tr>")

    def tot(per, key):
        return wg.get(per, {}).get(key, 0) + ss.get(per, {}).get(key, 0)

    rows.append(f"<tr><td {TD % 'left'}><b>Total</b></td>"
                f"<td {TD % 'right'}>{tot('q1','launches')}</td>"
                f"<td {TD % 'right'}>{tot('q1','graduated')}</td>"
                f"<td {TD % 'right'}>{tot('q2','launches')}</td>"
                f"<td {TD % 'right'}>{tot('q2','graduated')}</td></tr>")
    return '<table style="border-collapse:collapse;font-size:10pt">' + "".join(rows) + "</table>"


def _definitions():
    """Definitions section: a heading followed by plain <p> lines (no table)."""
    items = [
        "<b>Monthly Volume:</b> total trading volume over the trailing 30 days. WoW compares to the 30-day window ending 7 days earlier.",
        "<b>Organic volume:</b> excludes known internal/bot wallets.",
        "<b>Total Domains Onchain:</b> domains + subdomains + name tokens, spam-excluded.",
        "<b>Network Asset Value:</b> implied value of the underlying domain assets, derived from token prices (bonding curve pre-graduation, pool price post-graduation). Distinct from TVL.",
        "<b>MAU:</b> unique active wallets over the trailing 30 days.",
        "<b>Fractional Launches:</b> cumulative launches since inception.",
        "<b>Graduation rate:</b> of launches in the period, the share that have graduated (incl. buyouts).",
    ]
    return "<p><b>Definitions</b></p>" + "".join(f"<p>{x}</p>" for x in items)


def _quarter_label(report_friday):
    """Derive the quarter label from report_friday ('YYYY-MM-DD') so the heading
    tracks the calendar (Q2 -> Q3 on Jul 1) instead of being hard-coded."""
    try:
        q = (int(report_friday[5:7]) - 1) // 3 + 1
        return f"Q{q}"
    except Exception:
        return "Q"


def build_html(d, narrative):
    pd = d["premium_domains"]
    prem = []
    # Label is driven by the fractional_token.status field carried in the JSON,
    # never assumed: GRADUATION_SUCCESSFUL -> Graduated, GRADUATION_FAILED ->
    # Graduation failed, FRACTIONALIZED (on the bonding curve) -> Bonding Now.
    # Fallbacks cover data snapshots written before the status field existed.
    STATUS_LABEL = {
        "GRADUATION_SUCCESSFUL": "Graduated",
        "GRADUATION_FAILED": "Graduation failed",
        "FRACTIONALIZED": "Bonding Now",
    }
    if pd["live"]:
        lbl = STATUS_LABEL.get(pd["live"].get("status"), "Graduated")
        prem.append(f"{lbl}: {pd['live']['name']} (FDV {fmt_money_dollars(pd['live']['fdv_usd'])})")
    if pd["upcoming"]:
        lbl = STATUS_LABEL.get(pd["upcoming"].get("status"), "Bonding Now")
        prem.append(f"{lbl}: {pd['upcoming']['name']} (Blended FDV {fmt_money_dollars(pd['upcoming']['fdv_usd'])})")
    def ul(items):
        return "<ul>" + "".join(f"<li>{x}</li>" for x in items) + "</ul>"

    parts = [
        '<div style="font-family:Arial,sans-serif;font-size:11pt">',
        "<p>Hi team,</p>",
        f'<p>Weekly Commercial KPI report in GDrive and below. Live Daily Dashboard: '
        f'<a href="{DASHBOARD_URL}">{DASHBOARD_URL}</a> [user: d3, pw: d3demo]</p>',
        f"<p><b>{_quarter_label(d['report_friday'])} KPIs &middot; Week ending {narrative['week_ending']}</b></p>",
        f"<p><b>TLDR:</b> {narrative['tldr']}</p>",
        "<p><b>Key Wins</b></p>", ul(narrative.get("key_wins", [])),
        "<p><b>Key Updates</b></p>", ul(narrative.get("key_updates", [])),
        _kpi_table(d),
        '<p style="font-size:9pt;color:#666">Goal column reflects Q2 targets; Q3 goals coming soon.</p>',
        _definitions(),
        "<p><b>Fractional Performance</b></p>",
        _frac_table(d),
        _frac_launch_table(d),
        "<p><b>Premium Domains</b></p>", ul(prem),
        "<p><b>Registrars &ndash; BD</b></p>", ul(narrative.get("reg_bd", [])),
        "<p><b>Registrars &ndash; Integrations</b></p>", ul(narrative.get("reg_int", [])),
        "<p><b>Ecosystem Partners</b></p>", ul(narrative.get("ecosystem", [])),
        "<p><b>Next Steps</b></p>", ul(narrative.get("next_steps", [])),
        "</div>",
    ]
    return "".join(parts)


DASHBOARD_URL = "https://d3-kpi-dashboard-one.vercel.app"


def main():
    data = json.load(open(sys.argv[1]))
    narrative = json.load(open(sys.argv[2]))
    sys.stdout.write(build_html(data, narrative))


if __name__ == "__main__":
    main()
