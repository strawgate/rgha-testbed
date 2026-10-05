# Platform pilot simulation: results (2026-10-04)

`sim-ci.yml` mirrors the light jobs in Platform's `main.yml` (`resolve`,
`detect-changes`, `check` via alls-green, plus an OIDC job). `sim-agentic.yml`
mirrors a compiled gh-aw workflow: `pre_activation` → `activation` → `agent`
→ `safe_outputs` → `conclusion`. The agent job installs the real gh-aw
firewall (AWF v0.27.22 in rootless isolation mode), its pinned images and
Docker Compose, then runs a stand-in agent under the firewall that mostly
waits on the network.

Runners come from repo variables, with GitHub-hosted fallbacks:
`runs-on: ${{ vars.LIGHT_RUNNER || 'ubuntu-slim' }}` and
`${{ vars.AGENT_RUNNER || 'ubuntu-latest' }}`.

## Scenarios

| Scenario | Result |
|---|---|
| Baseline: variables unset, GitHub-hosted | ✅ |
| Light jobs on `rgha-light` (Modal gVisor, GitHub-only egress) | ✅ 4–8 s queue; github-script, artifacts, paths-filter, alls-green, OIDC token |
| Agent job on `rgha-agent` (Modal VM + Docker) | ✅ AWF firewall enforced (`polls=18 blocked=yes`), 252–262 s vs 267 s on `ubuntu-latest` |
| Same-repo PR (`pull_request`, paths filter) | ✅ result posted as a PR comment by `safe_outputs` |
| Second push to the PR (concurrency `cancel-in-progress`) | ✅ old run cancelled; its sandbox stopped after 18 s ($0.0004) |
| `/sim` comment (`issue_comment`) | ✅ |
| Fork PR | ✅ never reaches rgha: GitHub doesn't pass repo variables to fork PRs, so jobs fell back to GitHub-hosted. A fork job that names an rgha label directly is cancelled by class policy (`languages` on `rgha-small`). |
| Controller killed (`kill -9`) mid agent job, restarted 60 s later | ✅ job finished; restart stopped an orphaned idle runner and left the busy one alone; no leaked sandboxes |
| Controller host offline ~75 min (laptop network) | ⚠️ jobs waited, then ran after reconnecting with no intervention. The controller needs an always-on host. |
| Flip back: delete the variables | ✅ jobs go to GitHub-hosted |

## Compatibility gaps found and fixed (strawgate/rgha `feat/pilot-sim`)

- Modal runs the entrypoint as root, and the runner image has no sudoers
  entry for root, so `sudo` failed. On the VM runtime the runner now drops to
  the `runner` user, as on GitHub-hosted. On gVisor, no_new_privs blocks
  setuid, so the runner stays root and root gets a sudoers entry.
- Modal sets `PYTHONPATH=/pkg/:/root/`, which breaks pip (`Permission
  denied: '/root'`). It is unset now.
- No `docker compose` (AWF needs it). The Compose v2 plugin is added to the
  Docker layer.
- No `python` on PATH (alls-green needs it). `python3` and
  `python-is-python3` are added through backend `image_commands`.

## Metered cost (Modal usage meter)

| Job type | rgha | Platform's runner today | Ratio |
|---|---|---|---|
| Light job (avg of 57, ~9 s) | $0.00008 | `ubuntu-slim` $0.002 (1 min) | ~25× cheaper |
| Agent job (4.3 min, 3-min stand-in wait) | $0.0042 | `ubicloud-standard-2` $0.005 (5 min) | ~1.2× cheaper |

The agent job costs about $0.0024 in CPU, mostly ~50 s of setup (image pulls,
toolchains, apt), and $0.0018 in memory (Docker and containers hold ~1 GiB).
Each idle minute costs about $0.0007 against Ubicloud's $0.001. Baking the
images and toolchains into the Modal image would cut the setup cost.
