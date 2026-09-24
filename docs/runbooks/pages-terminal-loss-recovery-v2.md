# GitHub Pages terminal-loss recovery v2

## Purpose
Recover the verified state of `nagdkl/nagdkl.github.io` after WSL2/VM/terminal loss without relying on prior local state or replaying publication mutations.

## Canonical identities
- main: `0e872af12b2aee39bc06df49bedf4e5a3179dbdc`
- `index.md` blob: `2606d236549a1a43e9e5ba3684b888d784f18fe0`
- `_layouts/default.html` blob: `0b4de0aa8242c2d533d86ba50d59b7a63dd8a097`

## Runtime
`python3 scripts/recover_pages_after_terminal_loss_v2.py`

The runtime is read-only: fresh clone, identity verification, clean-checkout verification, and one bounded HTTP GET. It performs zero pushes, merges, releases, deployments, retries, or writes to an existing checkout.

## Evidence
Each run creates a private state directory under `~/.local/state/synergy-mesh/pages-recovery-v2/runs/<run-id>/` with `steps.log` and, on PASS, `receipt.json`.

## Failure semantics
Exit `78` means fail-closed BLOCKED. A missing/changed ref, blob drift, clone failure, DNS/HTTP failure, non-200 response, or missing content marker is never treated as PASS.

## Terminal-loss rule
Do not reconstruct the old `/tmp` checkout. Start again from the immutable remote GitHub state using this Git-saved launcher.

## Git-native v4 launcher

After the first Gitleaks-gated publication, `scripts/run_pages_recovery_v4.py` becomes the
canonical launcher source. It runs from any current directory, creates an isolated checkout,
verifies exact `main`, and delegates to the checked-in read-only verifier. The pre-publication
Drive/package transport is bootstrap-only and is not the long-term source of truth.
