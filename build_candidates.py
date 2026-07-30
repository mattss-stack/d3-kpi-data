#!/usr/bin/env python3
"""
Candidates block — the shortlist Matt writes The Read from.

We ship 10+ things a week, so a blank "what mattered most" box is not actionable.
This computes the deterministic half of the shortlist: what actually changed since
last week, ranked. The routine adds the Slack/meeting half (candidate causes, exec
questions asked this week), which needs sources this script can't reach.

Prior-week data comes from git history — the data JSON is committed daily, so the
repo is the archive. No separate snapshot store needed.

Renders as a scratch block at the top of the draft, marked DELETE BEFORE SEND.

Run: python3 build_candidates.py weekly_report_data.json [--days-back 7]
"""

import argparse
import json
import subprocess
import sys
from datetime import date, datetime, timedelta

REPO = "/root/d3-kpi-data"
DATA_FILE = "weekly_report_data.json"

# A metric move below both bars is noise and stays off the shortlist.
MIN_PCT_MOVE = 5.0
MIN_ABS_MOVE = 1000


def prior_data(as_of, days_back=7, repo=REPO, path=DATA_FILE):
    """The committed data JSON from ~days_back before as_of, or None.

    Picks the last commit at or before the cutoff rather than a fixed offset, so a
    missed daily cron run degrades to a slightly older baseline instead of failing.
    """
    cutoff = (as_of - timedelta(days=days_back)).isoformat()
    try:
        rev = subprocess.run(
            ["git", "-C", repo, "log", "--before", f"{cutoff} 23:59:59",
             "-1", "--format=%H", "--", path],
            capture_output=True, text=True, timeout=30, check=True).stdout.strip()
        if not rev:
            return None, None
        blob = subprocess.run(
            ["git", "-C", repo, "show", f"{rev}:{path}"],
            capture_output=True, text=True, timeout=30, check=True).stdout
        return json.loads(blob), rev[:8]
    except Exception as exc:  # noqa: BLE001 — no baseline is a degraded mode, not fatal
        print(f"[warn] could not read prior data: {exc}", file=sys.stderr)
        return None, None


def _flatten_kpis(d):
    """KPI leaf values keyed by dotted path, for diffing."""
    out = {}

    def walk(node, prefix):
        if isinstance(node, dict):
            for k, v in node.items():
                walk(v, f"{prefix}.{k}" if prefix else k)
        elif isinstance(node, (int, float)) and not isinstance(node, bool):
            out[prefix] = float(node)

    walk(d.get("kpis", {}), "")
    return out


def metric_moves(curr, prev):
    """Ranked list of what moved, biggest relative move first.

    Skips the *_pct and *_wow fields themselves — a change in a percentage field is
    a second derivative and reads as noise in a shortlist.
    """
    a, b = _flatten_kpis(curr), _flatten_kpis(prev)
    moves = []
    for key, now in a.items():
        if key.endswith(("_pct", "wow_pct")):
            continue
        # prior_* fields are last week's current values shifted into the prior slot.
        # Diffing them across two reports measures the calendar, not the business.
        if "prior" in key:
            continue
        then = b.get(key)
        if then is None or then == 0:
            continue
        delta = now - then
        pct = delta / abs(then) * 100
        if abs(pct) < MIN_PCT_MOVE or abs(delta) < MIN_ABS_MOVE:
            continue
        moves.append({"metric": key, "prior": then, "now": now,
                      "delta": delta, "pct": round(pct, 1)})
    moves.sort(key=lambda m: -abs(m["pct"]))
    return moves


def volume_highlights(curr):
    """The already-computed volume story, restated as shortlist lines."""
    vd = curr.get("volume_driver")
    if not vd:
        return ["volume_driver missing — run volume_diagnosis.py"]
    out = []
    t = vd["total"]
    out.append(f"volume {t['wow_pct']:+.1f}% WoW (${t['delta']:,.0f})")
    co = vd.get("cohorts", {})
    for k, c in co.items():
        out.append(f"{k} {c['wow_pct']:+.1f}%, {c['share_of_delta_pct']}% of the move")
    to = vd.get("true_organic") or {}
    if to.get("excluded_wallets"):
        out.append(f"true organic {to['wow_pct']:+.1f}% once {to['excluded_wallets']} "
                   f"machine-frequency wallets come out — the headline organic number "
                   f"overstates user decline")
    if vd.get("cliff"):
        c = vd["cliff"]
        out.append(f"{c['cohort']} broke on {c['date']} ({c['pct']:+.1f}%) — "
                   f"a dated event, so there is something to point at")
    if vd.get("base_inflation"):
        b = vd["base_inflation"]
        out.append(f"prior week ran {b['ratio']}x its trailing rate — part of the WoW% "
                   f"is the comparison base, worth saying out loud")
    cs = vd.get("count_vs_size") or {}
    if cs.get("reading"):
        out.append(f"shape: {cs['reading']}")
    return out


def build_candidates(curr, days_back=7):
    as_of = date.fromisoformat(curr.get("report_friday") or date.today().isoformat())
    prev, rev = prior_data(as_of, days_back)
    return {
        "baseline_commit": rev,
        "baseline_missing": prev is None,
        "volume": volume_highlights(curr),
        "moves": metric_moves(curr, prev) if prev else [],
        # Filled by the routine, which has the Slack/meeting sources.
        "cause_candidates": [],
        "exec_questions": [],
        "shipped_that_moved_a_number": [],
    }


def render_block(c):
    """Scratch HTML for the top of the draft. Deleted before send."""
    L = ['<div style="border:2px dashed #c00;padding:10px;background:#fffbe6;font-size:10pt">',
         '<p><b>CANDIDATES — internal scratch. DELETE THIS BLOCK BEFORE SENDING.</b></p>',
         '<p>Pick one or two and write The Read. This is retrieval, not judgment.</p>']
    if c["baseline_missing"]:
        L.append('<p><i>No prior-week baseline found in git; move list unavailable.</i></p>')
    L.append("<p><b>Volume</b></p><ul>"
             + "".join(f"<li>{x}</li>" for x in c["volume"]) + "</ul>")
    if c["moves"]:
        L.append("<p><b>What moved vs last week</b></p><ul>")
        for m in c["moves"][:10]:
            L.append(f"<li>{m['metric']}: {m['prior']:,.0f} &rarr; {m['now']:,.0f} "
                     f"({m['pct']:+.1f}%)</li>")
        L.append("</ul>")
    for key, label in (("cause_candidates", "Candidate causes (sourced)"),
                       ("exec_questions", "Exec questions asked this week"),
                       ("shipped_that_moved_a_number", "Shipped items that moved a number")):
        items = c.get(key) or []
        L.append(f"<p><b>{label}</b></p>")
        L.append("<ul>" + "".join(f"<li>{x}</li>" for x in items) + "</ul>" if items
                 else f"<p><i>[routine: fill {key} from Slack/Granola, with links]</i></p>")
    L.append("</div>")
    return "".join(L)


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("data")
    ap.add_argument("--days-back", type=int, default=7)
    ap.add_argument("--html", action="store_true")
    a = ap.parse_args()
    curr = json.load(open(a.data))
    c = build_candidates(curr, a.days_back)
    if a.html:
        print(render_block(c))
        return
    print(f"baseline: {c['baseline_commit'] or 'MISSING'}")
    print("\nVolume:")
    for x in c["volume"]:
        print("  -", x)
    print(f"\nWhat moved ({len(c['moves'])} above threshold):")
    for m in c["moves"][:10]:
        print(f"  - {m['metric']}: {m['prior']:,.0f} -> {m['now']:,.0f} ({m['pct']:+.1f}%)")
    print("\ncause_candidates / exec_questions / shipped_that_moved_a_number: routine fills these.")


if __name__ == "__main__":
    main()
