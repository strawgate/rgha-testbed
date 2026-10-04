# rgha-testbed

End-to-end test repo for [rgha](https://github.com/strawgate/rgha): every
workflow here runs on rgha-managed Modal sandboxes.

| Workflow | Class | Exercises | Expected |
|---|---|---|---|
| `smoke` | `rgha-tiny` (untrusted, warm, GitHub-only egress) | checkout, egress block | success; `example.com` blocked |
| `languages` | `rgha-small` (untrusted, egress allowlist) | `setup-node` + npm, `setup-python` + PyPI | success |
| `burst` | `rgha-tiny` | N parallel jobs, scale-out, `max_runners` | success; all jobs run |
| `docker` | `rgha-docker` (trusted, Modal VM runtime) | `docker build`, container job, `services:` | success on `main` |
| `policy-probe` | `rgha-docker` | a PR aimed at a trusted class | **cancelled** by rgha |

## Run the controller

```bash
# released binary (https://github.com/strawgate/rgha/releases)
GITHUB_TOKEN=$(gh auth token) rgha run --config controller/rgha.toml --metrics-addr 127.0.0.1:9464

# or the container image
docker run --rm -e GITHUB_TOKEN -e MODAL_TOKEN_ID -e MODAL_TOKEN_SECRET \
  -v "$PWD/controller/rgha.toml:/etc/rgha/rgha.toml:ro" -p 9464:9464 \
  ghcr.io/strawgate/rgha:0.1.0
```

Then trigger workflows:

```bash
gh workflow run smoke.yml
gh workflow run languages.yml
gh workflow run burst.yml -f jobs=10 -f seconds=5
gh workflow run docker.yml
```

To run the policy probe, open a PR that changes anything under `probe/`.

## Results (rgha v0.1.0, 2026-10-04)

Controller: released `rgha` v0.1.0 macOS binary, config in `controller/rgha.toml`.

| Run | Outcome | Notes |
|---|---|---|
| `smoke` (push) | ✅ | warm runner, pickup 0.1 s, job 6.4 s; `example.com` blocked |
| `languages` (push) | ✅ node, ✅ python | `setup-node` + npm, `setup-python` + PyPI through the egress allowlist; pickup ~5 s cold |
| `docker` (push) | ✅ build, ✅ services | `docker build`/`run`, `container:` job + `redis` service on the Modal VM runtime; pickup ~5 s |
| `burst` (20 jobs × 10 s) | ✅ 21/21 | 44 s wall; pickup p50 4.1 s, p90 4.8 s, max 15.3 s (queued behind `max_runners = 12`) |
| PR #1 → `policy-probe` | ✅ **cancelled** in 3 s | rgha rejected a `pull_request` job aimed at the trusted Docker class |
| PR #1 → `smoke`, `languages` | ✅ | untrusted classes accept PRs |

Estimated Modal spend for the whole session was about $0.04 (including warm-runner idle
time). The same jobs on per-minute GitHub-hosted runners would cost about $0.17.

## Speed work (2026-10-04)

| Change | Before | After |
|---|---|---|
| Preloaded image (`[backends.modal.preload]`) | `setup-node` 4 s, `setup-python` 9 s | 0 s, 1 s |
| | node job 14.6 s, python job 19.5 s | 6.9 s, 8.1 s |
| Cheap warm runner (0.125 core / 256 MiB request, 2 cores / 2 GiB limit) | ~$0.06/h at 0.25 core / 1 GiB | ~$0.024/h, pickup still 0.1 s |
| `warm_for_secs = 600` | warm 24/7 | pool switched off 10 min after the last job |
| Region pinned to `us-east` | cold pickup 4.0 s avg | 3.6 s avg; within noise, not worth 1.75× price |
| Memory-snapshot "hibernated" runner | n/a | **no-go**: restored runner shows online, but never took the job (still queued after 7.5 min) |

## GitHub-hosted vs rgha (2026-10-04, rgha `main` after v0.1.1)

`compare.yml` runs the same jobs on `ubuntu-latest` and on rgha classes; 3
rounds = 42 jobs per side. Analyzed with
`scripts/compare.py <controller-log> <run ids>`. Queue = job `started_at -
created_at`; duration = `completed_at - started_at`. GitHub cost uses the
private-repo price ($0.006/min, rounded up per job); standard runners are
free on public repos. rgha cost is the controller's per-job estimate.

**Cold** (scale to zero; one warm `rgha-tiny` runner within 10 min of activity):

| job | GitHub queue p50 | rgha queue p50 | GitHub dur p50 | rgha dur p50 | GitHub $/job | rgha $/job |
|---|---|---|---|---|---|---|
| smoke (`rgha-tiny`) | 5.0 s | 7.0 s | 4.0 s | 6.0 s | 0.00600 | 0.00083 |
| node (`rgha-small`) | 3.0 s | 8.0 s | 6.0 s | 6.0 s | 0.00600 | 0.00092 |
| python (`rgha-small`) | 3.0 s | 8.0 s | 8.0 s | 8.0 s | 0.00600 | 0.00105 |
| docker (`rgha-docker`) | 5.0 s | 7.0 s | 12.0 s | 5.0 s | 0.00600 | 0.00085 |
| burst ×10 (`rgha-tiny`) | 5.0 s | 8.0 s | 7.0 s | 7.0 s | 0.00600 | 0.00083 |
| **42 jobs** | | | | | **$0.252** | **$0.036** (controller total incl. idle: $0.040) |

Of rgha's ~8 s queue, ~3–4 s is GitHub-side (job created → assigned to the scale
set) and ~4–5 s is cold pickup (only 3/33 tiny jobs found a warm runner).

**Warm pools sized to the burst** (`min_idle`: tiny 11, small 2, docker 1; `warm_for_secs = 600`):

| job | GitHub queue p50 | rgha queue p50 | GitHub dur p50 | rgha dur p50 | rgha $/job |
|---|---|---|---|---|---|
| smoke | 4.0 s | 3.0 s | 5.0 s | 6.0 s | 0.00125 |
| node | 4.0 s | 4.0 s | 7.0 s | 8.0 s | 0.00190 |
| python | 5.0 s | 4.0 s | 9.0 s | 7.0 s | 0.00185 |
| docker | 5.0 s | 3.0 s | 11.0 s | 5.0 s | 0.00546 |
| burst ×10 | 5.0 s | 4.0 s | 7.0 s | 8.0 s | 0.00124 |

Warm pickups: tiny 33/34, small 6/8, docker 3/5. The jobs themselves cost $0.069
(3.7× less than GitHub's $0.252). The **controller total** of $0.174 also covers
the priming jobs and the 10-minute idle tail of 14 warm runners after the last
job, against roughly $0.28 for the same jobs on GitHub. At this low volume the
idle tail dominates; it needs throughput, or smaller and smarter warm pools, to
pay off.

**Takeaways**
- Scale-to-zero is ~7× cheaper than per-minute hosted runners, at the cost of ~3–4 s more queue time.
- With warm pools, rgha matched or beat GitHub-hosted queue times, and Docker builds ran ~2× faster (5 s vs 11–12 s).
- Warm pools cost real money at low volume: keep warm requests tiny (the docker class's 1 core / 4 GiB idle request was the most expensive part of the tail), and size pools to demand (strawgate/rgha#16).
- Hardware differs: public-repo `ubuntu-latest` is 4 vCPU / 16 GB; these rgha classes request 0.125–1 core and burst to 2.

**Adaptive warm pools + tiny idle requests** (every class requests 0.125 core
and 256–512 MiB when idle; `warm_max`: tiny 4, small 2, docker 1; +1 warm runner
per minute while jobs start cold, −1 per 5 minutes quiet):

| job | GitHub queue p50 | rgha queue p50 | GitHub dur p50 | rgha dur p50 | rgha $/job |
|---|---|---|---|---|---|
| smoke | 4.0 s | 7.0 s | 5.0 s | 5.0 s | 0.00085 |
| node | 3.0 s | 3.0 s | 9.0 s | 6.0 s | 0.00118 |
| python | 4.0 s | 6.0 s | 8.0 s | 7.0 s | 0.00100 |
| docker | 5.0 s (p90 39 s) | 4.0 s | 10.0 s | 5.0 s | 0.00112 |
| burst ×10 | 5.0 s | 7.5 s | 7.5 s | 8.0 s | 0.00083 |

The warm targets grew slowly: tiny 0→1→2→3, small 0→1→2, docker 0→1. After
the last round they shrank one step at a time and reached zero 14 minutes
later. Warm pickups: docker 2/5, small 3/8, tiny 3/34 (a 10-job burst is
still mostly cold by design).

| Configuration (42 jobs per side) | Queue p50 (rgha) | rgha controller total | vs GitHub $0.252 |
|---|---|---|---|
| Scale to zero (+1 warm tiny runner) | 7–8 s | $0.040 | 6.3× cheaper |
| Fixed warm pools sized to the burst | 3–4 s | $0.174 | 1.4× cheaper |
| **Adaptive warm + tiny idle requests** | 3–7.5 s | **$0.061** | **4.1× cheaper** |
