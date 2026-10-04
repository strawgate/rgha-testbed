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
