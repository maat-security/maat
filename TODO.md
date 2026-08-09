# Maat — TODO

Prioritized list for picking this back up. See `README.md`'s **Implementation Status** section for the full working/gaps/not-started breakdown this is derived from, and `QA.md` for the manual test plan that should run before any of this ships.

## High Priority — Closes Out the v1 MVP

The PRD's own MVP scope (`README.md` Roadmap → v1) isn't fully done without these three:

1. **Have I Been Pwned integration.** `metrics.py`'s `_compute_exposure_freshness()` already reads a `breached` attribute off Identity nodes — nothing sets it yet. Needs: a k-anonymity HIBP client (hash prefix only ever leaves the device, per the design principle already stated in the README), run in the background per PRD section 7, wired to set `breached: True` on the matching Identity node(s).
2. **Self-contained HTML export.** Listed in MVP scope (section 8 of the PRD) and referenced in the README's "What Maat Does" section — no code exists for it at all. Should export score + breakdown + gaps + remediation history, no secrets, as one static HTML file the user chooses where to save.
3. **KeePass XML importer.** The PRD's import formats list includes it alongside 1Password/Bitwarden/CSV; only those three exist in `src/importers/`. Same shape as the existing importers — `parse(filepath) -> list[account dict]`, using `_shared.py`'s helpers. KeePass XML structure is public and documented; no test fixtures for it exist yet either.

## Medium Priority

4. **Automated test suite.** Every module in this repo has been verified during development with throwaway scripts (drive the code directly, assert, delete the script) — none of that is committed. Worth turning the more valuable of those into a real `pytest` suite under `tests/`, particularly: `store.py`'s encryption round-trip, `graph.py`'s blast-radius/cut-vertex/cycle math, `metrics.py`'s four score components against known scenarios, and `remediation.py`'s five `_apply_fix` mutations. Add `pytest` to `requirements.txt` (dev-only) and a CI job that runs it on PRs.
5. **Graph visualization screen.** PRD section 13 calls for this explicitly ("disponible como herramienta de exploración, no como pantalla principal"). The graph and all its query functions (`get_blast_radius`, `get_cut_vertices`, `get_cycles`) already exist — this is purely a new `ui/` frame to render them, no new engine work.
6. **Human QA pass.** Run `QA.md` for real on Windows, macOS, and Linux, with real (throwaway) exports from actual 1Password/Bitwarden accounts — every importer test so far has used hand-built synthetic fixtures in scratch scripts, not a real export file from the real app.

## Deferred On Purpose

7. **API integrations** (GitHub, Google Workspace, Microsoft Entra) — explicitly pushed to the end per project decision. `ui/onboarding.py`'s "Connect Integration" panel is wired to a "Coming Soon" dialog and nothing else. When this starts: GitHub first (PRD section 7 lists it as the only MVP-scoped integration), needs OAuth or PAT-based auth, a client for 2FA/PAT/SSH-key/session status, and — the reason this is last — a real answer to the PRD's own risk note in section 10: an integration with write scope becomes the graph's highest-blast-radius node.

## Later Phases (PRD)

8. **Drift monitoring** (Roadmap v2) — periodic re-import, change detection, the "you haven't reviewed these 3 critical accounts in 90 days" review session. `metrics.py`'s staleness check (`_is_stale`, `STALE_AFTER_DAYS`) already exists as the underlying signal; this phase is the UI/scheduling layer on top of it.
9. **Published native installers** (Roadmap v4) — `build.spec` and `.github/workflows/build.yml` exist and build successfully locally, but the workflow triggers on a `v*` tag push and no such tag has ever been pushed. First real release is just pushing a tag once the above is far enough along to be worth shipping.
10. **The narrow automated-remediation exception** (PRD section 10: e.g. auto-revoking an expired GitHub PAT) — blocked on #7. Don't build this before there's an actual API client with a real minimal-scope token to revoke.

## Notes for Next Session

- `.venv/` is gitignored and not committed — recreate it (see `README.md` Getting Started) before running anything.
- Delete any `_scratch_*` files or `scratch_*.py` scripts left in the repo root before committing — they're throwaway verification scripts, never meant to ship. None should currently be present, but check.
- `dist/`, `build/`, and `__pycache__/` are gitignored; if a PyInstaller run leaves them around locally, clean them up before diffing.
