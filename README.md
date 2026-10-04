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
