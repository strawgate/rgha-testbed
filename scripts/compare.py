#!/usr/bin/env python3
"""Summarize compare.yml runs: queue time, duration and cost per runner type.

usage: compare.py <controller-log> <run-id> [<run-id> ...]

- queue = job started_at - created_at; duration = completed_at - started_at
- GitHub-hosted cost: each job rounded up to whole minutes at the private-repo
  Linux 2-core price ($0.006/min). Standard runners are free on public repos.
- rgha cost: the controller's per-job estimate from its log ("runner finished"
  cost_usd: busy time at the CPU/memory caps, idle time at the requests).
"""
import json, math, re, statistics, subprocess, sys
from datetime import datetime

GH_PER_MIN = 0.006
REPO = "strawgate/rgha-testbed"


def ts(s):
    return datetime.fromisoformat(s.replace("Z", "+00:00"))


def jobs(run_id):
    out = subprocess.run(
        ["gh", "api", "--paginate", f"repos/{REPO}/actions/runs/{run_id}/jobs?per_page=100", "--jq", ".jobs[] | @json"],
        check=True, capture_output=True, text=True,
    ).stdout
    return [json.loads(line) for line in out.splitlines() if line.strip()]


def rgha_costs(log):
    """runner name -> cost estimate (USD) from the controller's log."""
    cost = {}
    for line in open(log, encoding="utf-8", errors="replace"):
        line = re.sub(r"\x1b\[[0-9;]*m", "", line)
        # " cost_usd=" with a leading space: not the cumulative total_cost_usd.
        m = re.search(r"runner finished .* runner=(\S+) .* cost_usd=\"([0-9.]+)\"", line)
        if m:
            cost[m.group(1)] = float(m.group(2))
    return cost


def main():
    log, run_ids = sys.argv[1], sys.argv[2:]
    cost = rgha_costs(log)
    rows = []
    for rid in run_ids:
        for j in jobs(rid):
            if j["conclusion"] != "success":
                continue
            m = re.match(r"(\w+) \(([^,)]+)", j["name"])
            if not m:
                continue
            kind, runner = m.group(1), m.group(2)
            queue = (ts(j["started_at"]) - ts(j["created_at"])).total_seconds()
            dur = (ts(j["completed_at"]) - ts(j["started_at"])).total_seconds()
            hosted = runner.startswith("ubuntu")
            usd = math.ceil(max(dur, 1) / 60) * GH_PER_MIN if hosted else cost.get(j["runner_name"], float("nan"))
            rows.append((kind, "github" if hosted else runner, queue, dur, usd))

    print(f"{'job':8} {'runner':12} {'n':>3} {'queue p50':>9} {'queue p90':>9} {'dur p50':>8} {'$/job':>9}")
    for kind in ["smoke", "node", "python", "docker", "burst"]:
        for side in sorted({r[1] for r in rows if r[0] == kind}, key=lambda s: s != "github"):
            sel = [r for r in rows if r[0] == kind and r[1] == side]
            q = sorted(r[2] for r in sel)
            d = sorted(r[3] for r in sel)
            c = [r[4] for r in sel if not math.isnan(r[4])]
            p90 = q[min(len(q) - 1, int(len(q) * 0.9))]
            print(f"{kind:8} {side:12} {len(sel):>3} {statistics.median(q):>8.1f}s {p90:>8.1f}s {statistics.median(d):>7.1f}s "
                  f"{(statistics.mean(c) if c else float('nan')):>9.5f}")
    for side in ["github", "rgha"]:
        sel = [r for r in rows if (r[1] == "github") == (side == "github")]
        tot = sum(r[4] for r in sel if not math.isnan(r[4]))
        print(f"total {side:7} jobs={len(sel):3}  cost=${tot:.4f}")


if __name__ == "__main__":
    main()
