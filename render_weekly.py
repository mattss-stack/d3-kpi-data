#!/usr/bin/env python3
"""Self-contained renderer for D3's weekly KPI report (stdlib only).

Ported from /root/kpi-report/publish_weekly_gdoc.py. Produces byte-identical
table HTML, but reads data + narrative from JSON files instead of calling
weekly_report.build_weekly_data() / Drive. No third-party imports, no
dependency on the weekly_report module.

Run: python3 render_weekly.py <data.json> <narrative.json> > out.html
"""
import json
import sys


# --- Inlined formatters (copies of weekly_report's, with None guards) ---------
def fmt_money_dollars(usd):
    if usd is None:
        return "—"
    if usd >= 1_000_000:
        return f"${usd / 1_000_000:.1f}M"
    if usd >= 1_000:
        return f"${usd / 1_000:.1f}K"
    return f"${usd:.0f}"


def fmt_count(n):
    if n is None:
        return "—"
    return f"{int(round(n)):,}"


def fmt_pct(p):
    if p is None:
        return "  —"
    sign = "+" if p >= 0 else ""
    return f"{sign}{p:.1f}%"


def _pct(p):
    return fmt_pct(p).strip()


def _goal(v, target, suffix):
    return f"{v / target * 100:.0f}% to {suffix}" if v is not None else ""


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
        row("Network Asset Value", money(nav["last_end"]), money(nav["prior_end"]), nav["wow_pct"], nav_goal),
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


def _lpgap_table(d):
    """Premium Domain Economics — owner fees vs. the LP tier gap (Bob, ICANN Seville).
    Returns the full HTML section (heading + intro + native table + caveat), or "" if no data."""
    lg = d.get("premium_lp_gap")
    if not lg or not lg.get("names"):
        return ""
    MONTHS = ["", "Jan", "Feb", "Mar", "Apr", "May", "Jun", "Jul", "Aug", "Sep", "Oct", "Nov", "Dec"]
    money = fmt_money_dollars

    def ll(dt):                                   # 'YYYY-MM-DD' -> "Dec '25"
        if not dt:
            return "&mdash;"
        try:
            return f"{MONTHS[int(dt[5:7])]} &rsquo;{dt[2:4]}"
        except Exception:
            return dt

    def pf(x):                                    # absolute %, "—" when not live
        return "&mdash;" if x is None else f"{x:.0f}%"

    def fee(n, key, live):                        # period fee, "—" if not live
        return "&mdash;" if not live else money(n[key])

    # Single-row header only: Google Docs' HTML import does not reliably honor
    # rowspan/colspan, so grouped headers collapse and misalign. The "owner fees"
    # vs "% volume in pool" grouping is carried in the intro text instead.
    cols = ["Domain", "Launch", "Volume", "Raise",
            "Q1 fees", "Q2 fees", "30d fees", "Q1 %", "Q2 %", "30d %"]
    head = "<tr>" + "".join(
        f'<th {TH % ("left" if i == 0 else "right")}>{c}</th>' for i, c in enumerate(cols)
    ) + "</tr>"
    rows = [head]
    for n in lg["names"]:
        rows.append(
            f'<tr><td {TD % "left"}>{n["domain"]}</td>'
            f'<td {TD % "right"}>{ll(n["launch_date"])}</td>'
            f'<td {TD % "right"}>{money(n["volume_total"])}</td>'
            f'<td {TD % "right"}>{money(n["cash_out_to_owner"] or 0)}</td>'
            f'<td {TD % "right"}>{fee(n, "fees_q1", n["live_q1"])}</td>'
            f'<td {TD % "right"}>{fee(n, "fees_q2", n["live_q2"])}</td>'
            f'<td {TD % "right"}>{fee(n, "fees_t30d", n["live_t30d"])}</td>'
            f'<td {TD % "right"}>{pf(n["pct_q1"])}</td>'
            f'<td {TD % "right"}>{pf(n["pct_q2"])}</td>'
            f'<td {TD % "right"}>{pf(n["pct_t30d"])}</td></tr>'
        )
    t = lg["totals"]
    tot_vol = sum(n["volume_total"] for n in lg["names"])
    rows.append(
        f'<tr><td {TD % "left"}><b>TOTAL</b></td><td {TD % "right"}></td>'
        f'<td {TD % "right"}><b>{money(tot_vol)}</b></td>'
        f'<td {TD % "right"}><b>{money(t["cash_out_to_owner"])}</b></td>'
        f'<td {TD % "right"}><b>{money(t["fees_q1"])}</b></td>'
        f'<td {TD % "right"}><b>{money(t["fees_q2"])}</b></td>'
        f'<td {TD % "right"}><b>{money(t["fees_t30d"])}</b></td>'
        f'<td {TD % "right"}><b>{pf(t["pct_q1"])}</b></td>'
        f'<td {TD % "right"}><b>{pf(t["pct_q2"])}</b></td>'
        f'<td {TD % "right"}><b>{pf(t["pct_t30d"])}</b></td></tr>'
    )
    table = '<table style="border-collapse:collapse;font-size:10pt">' + "".join(rows) + "</table>"
    # Lead with dollars: earned vs. possible pool fees and the gap. "Possible" = what
    # each period would have earned with 100% of volume in the 0.3% pool, i.e. its
    # actual fees grossed up by its capture rate, summed across Q1+Q2.
    earned = t["fees_q1"] + t["fees_q2"]
    possible = ((t["fees_q1"] / (t["pct_q1"] / 100) if t["pct_q1"] else 0)
                + (t["fees_q2"] / (t["pct_q2"] / 100) if t["pct_q2"] else 0))
    gap = possible - earned
    intro = (
        f"Top 10 names by volume. Owners earned {money(earned)} of a possible {money(possible)} in pool fees "
        f"this quarter &mdash; a {money(gap)} gap, because trading keeps migrating from their locked 0.3% pool "
        f"to the cheaper 0.05% tier where they earn nothing (e.g. rides.com: high volume, low capture). The % "
        f"columns are each name&rsquo;s share of volume that still lands in the 0.3% pool."
    )
    caveat = (
        f"Launch = first-trade date; &ldquo;&mdash;&rdquo; = not live that period. Cohort fee capture fell "
        f"{pf(t['pct_q1'])} &rarr; {pf(t['pct_q2'])} Q1&rarr;Q2 (TOTAL row); the 30d figure "
        f"({pf(t['pct_t30d'])}) is fresh launches seeding new 0.3% liquidity, not recovery. Escalate the "
        f"locked-tier default to leadership."
    )
    return (
        "<p><b>Premium Domain Economics &mdash; owner fees vs. the LP tier gap</b></p>"
        f"<p>{intro}</p>" + table +
        f'<p style="font-size:9pt;color:#666">{caveat}</p>'
    )


def build_html(d, narrative):
    pd = d["premium_domains"]
    prem = []
    if pd["live"]:
        prem.append(f"Live: {pd['live']['name']} (FDV {fmt_money_dollars(pd['live']['fdv_usd'])})")
    if pd["upcoming"]:
        prem.append(f"Upcoming: {pd['upcoming']['name']} (Blended FDV {fmt_money_dollars(pd['upcoming']['fdv_usd'])})")
    def ul(items):
        return "<ul>" + "".join(f"<li>{x}</li>" for x in items) + "</ul>"

    def _tlds_section(s):
        """Render narrative['tlds'] like '15 partners; 7 in flight, ...' as a heading + 2-bullet ul.
        Splits on the first ';' into a count line and a status line. Omitted if no value."""
        if not s:
            return ""
        parts = [p.strip() for p in s.split(";", 1)]
        bullets = [parts[0]] + ([parts[1]] if len(parts) > 1 else [])
        return "<p><b>TLDs</b></p>" + ul(bullets)

    parts = [
        '<div style="font-family:Arial,sans-serif;font-size:11pt">',
        "<p>Hi team,</p>",
        f'<p>Weekly Commercial KPI report in GDrive and below. Live Daily Dashboard: '
        f'<a href="{DASHBOARD_URL}">{DASHBOARD_URL}</a> [user: d3, pw: d3demo]</p>',
        f"<p><b>Q2 KPIs &middot; Week ending {narrative['week_ending']}</b></p>",
        f"<p><b>TLDR:</b> {narrative['tldr']}</p>",
        "<p><b>Key Wins</b></p>", ul(narrative.get("key_wins", [])),
        "<p><b>Key Updates</b></p>", ul(narrative.get("key_updates", [])),
        _kpi_table(d),
        _definitions(),
        "<p><b>Fractional Performance</b></p>",
        _frac_table(d),
        _frac_launch_table(d),
        "<p><b>Premium Domains</b></p>", ul(prem),
        _lpgap_table(d),
        _tlds_section(narrative.get("tlds")),
        "<p><b>Registrars &ndash; BD</b></p>", ul(narrative.get("reg_bd", [])),
        "<p><b>Registrars &ndash; Integrations</b></p>", ul(narrative.get("reg_int", [])),
        "<p><b>Ecosystem Partners</b></p>", ul(narrative.get("ecosystem", [])),
        "<p><b>Next Steps</b></p>", ul(narrative.get("next_steps", [])),
        "<p>Let me know any feedback, thanks!</p>",
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
