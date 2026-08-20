#!/usr/bin/env python3
"""Self-contained renderer for D3's weekly KPI report (stdlib only).

Structure follows the EOW Scorecard format Matt settled on 2026-08-07 and rebuilt
2026-08-20: subject, heading, one links line, TLDR, Key Wins, Key Updates, Product
Updates, Next Steps. Nothing else.

What was removed on 2026-08-20, and why, so it does not creep back:
  - The KPI metrics table, Fractional Performance, Premium Domains, Registrars BD /
    Integrations, Ecosystem Partners and Definitions. All KPIs live in Metabase
    dashboard 57 now, for access control. The report links there once at the top.
  - The Read. Matt's call: it added no value, and a generated judgment reads like a
    real one.
  - The Volume Driver block. Volume folds into the TLDR as computed figures plus, at
    most, one causal sentence the routine has a dated source for.
  - The "EMAIL ENDS HERE" divider and the whole below-the-line tail. It existed
    because the full report lived on the Vercel dashboard's Weekly tab; that front
    end was retired 2026-08-20.
  - The candidates scratch block, which existed to help Matt write The Read.

Run: python3 render_weekly.py <data.json> <narrative.json> > out.html
"""
import json
import math
import sys

METABASE_URL = "https://metabase-prod.d3.app/dashboard/57-doma-kpi"
PRODUCT_BOARD_URL = ("https://app.notion.com/p/d3global/285d0d86d2708011ade2ee589c633509"
                     "?v=28fd0d86d2708052bba9000c38a4269b")


def _trunc1(x):
    """Truncate toward zero to 1 decimal (Matt's convention: never round up)."""
    return math.floor(abs(x) * 10) / 10.0


def fmt_money_dollars(usd):
    if usd is None:
        return None
    if usd >= 1_000_000:
        return f"${_trunc1(usd / 1_000_000):.1f}M"
    if usd >= 1_000:
        return f"${_trunc1(usd / 1_000):.1f}K"
    return f"${int(usd)}"


def fmt_count(n):
    if n is None:
        return None
    return f"{int(round(n)):,}"


def fmt_pct(p):
    if p is None:
        return None
    sign = "+" if p >= 0 else "-"
    return f"{sign}{_trunc1(p):.1f}%"


TH = 'style="border:1px solid #ccc;padding:5px 9px;background:#f3f3f3;text-align:left;font-weight:bold"'
TD = 'style="border:1px solid #ccc;padding:5px 9px;text-align:left;vertical-align:top"'


def _quarter_label(report_friday):
    """Derive the quarter from report_friday ('YYYY-MM-DD') so the heading tracks
    the calendar (Q2 -> Q3 on Jul 1) instead of being hard-coded."""
    try:
        q = (int(report_friday[5:7]) - 1) // 3 + 1
        return f"Q{q}"
    except Exception:
        return "Q"


def metrics_sentence(d):
    """The one numeric sentence in the report, computed here so the prose can never
    disagree with the data. Monthly Volume pairs the 30-day dollar with the 30-day
    rolling WoW (never the weekly WoW: pairing a 30-day dollar with a 7-day percent
    is the error that used to make the TLDR contradict itself). Returns '' when
    neither figure is available, so a data gap shortens the TLDR instead of
    printing a placeholder."""
    kpis = d.get("kpis") or {}
    parts = []

    mv = kpis.get("monthly_volume") or {}
    dollars = fmt_money_dollars(mv.get("headline_30d"))
    wow = fmt_pct(mv.get("rolling_30d_pct"))
    if dollars:
        parts.append(f"Monthly Volume {dollars}" + (f" ({wow} WoW)" if wow else ""))

    mau = kpis.get("mau") or {}
    mau_v = fmt_count(mau.get("last_end"))
    mau_wow = fmt_pct(mau.get("wow_pct"))
    if mau_v:
        parts.append(f"MAU {mau_v}" + (f" ({mau_wow} WoW)" if mau_wow else ""))

    return ("; ".join(parts) + ".") if parts else ""


def _ul(items):
    items = [str(x) for x in (items or []) if str(x).strip()]
    if not items:
        return ""
    return "<ul>" + "".join(f"<li>{x}</li>" for x in items) + "</ul>"


PRODUCT_COLS = [
    ("idea", "Idea"),
    ("owner", "Owner"),
    ("impact", "Expected impact"),
    ("status", "Status"),
    ("date", "Expected date"),
    ("this_week", "This week"),
]


def _product_table(rows):
    """Inder's format. Single header row and no spans: Drive's HTML to Doc
    conversion silently drops rowspan/colspan."""
    if not rows:
        return ""
    out = ['<table style="border-collapse:collapse;font-size:10pt"><tr>']
    out += [f"<th {TH}>{label}</th>" for _, label in PRODUCT_COLS]
    out.append("</tr>")
    for r in rows:
        out.append("<tr>")
        for key, _ in PRODUCT_COLS:
            out.append(f"<td {TD}>{(r.get(key) or '').strip()}</td>")
        out.append("</tr>")
    out.append("</table>")
    return "".join(out)


def build_html(d, narrative, email=False):
    """`email` is accepted and ignored. The report and the email are now the same
    document; the flag stays so older callers do not break."""
    tldr = (narrative.get("tldr") or "").strip()
    metrics = metrics_sentence(d)
    if metrics:
        tldr = (tldr + " " + metrics).strip() if tldr else metrics

    parts = [
        '<div style="font-family:Arial,sans-serif;font-size:11pt">',
        (f"<p><b>Subject:</b> {narrative['subject']}</p>" if narrative.get("subject") else ""),
        f"<p><b>{_quarter_label(d.get('report_friday',''))} KPIs, week ending "
        f"{narrative.get('week_ending','')}</b></p>",
        f'<p><i>All KPIs live in Metabase: <a href="{METABASE_URL}">Doma KPI dashboard</a>. '
        f'Full product board <a href="{PRODUCT_BOARD_URL}">here</a>.</i></p>',
        f"<p><b>TLDR</b></p><p>{tldr}</p>",
        "<p><b>Key Wins</b></p>", _ul(narrative.get("key_wins")),
        "<p><b>Key Updates</b></p>", _ul(narrative.get("key_updates")),
    ]

    rows = narrative.get("product_rows") or []
    if rows:
        parts += [
            "<p><b>Product Updates</b></p>",
            f'<p>What product and engineering have shipped and have in progress. '
            f'Full board <a href="{PRODUCT_BOARD_URL}">here</a>.</p>',
            _product_table(rows),
        ]

    parts += ["<p><b>Next Steps</b></p>", _ul(narrative.get("next_steps")), "</div>"]
    return "".join(parts)


def main():
    args = [a for a in sys.argv[1:] if not a.startswith("--")]
    email = "--email" in sys.argv[1:]
    data = json.load(open(args[0]))
    narrative = json.load(open(args[1]))
    sys.stdout.write(build_html(data, narrative, email=email))


if __name__ == "__main__":
    main()
