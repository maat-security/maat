# Maat — TODO

Prioritized list for picking this back up. See `README.md`'s **Implementation Status** section for the full working/gaps/not-started breakdown this is derived from, and `QA.md` for the manual test plan that should run before any of this ships.

## High Priority — Closes Out the v1 MVP

~~1. **Have I Been Pwned integration.**~~ Done — `src/hibp.py` is a k-anonymity Pwned Passwords client (only a 5-character hash prefix ever leaves the device). Every importer now calls it alongside password-reuse detection and sets `breached`/`breach_check_failed` on the account dict; `ui/onboarding.py` runs the whole import in a background thread so the network round trips don't freeze the UI. `metrics.py` surfaces a matched breach as a prioritized `"breached"` gap in consequence language, and `remediation.py` has a runbook + fix mutation for it. A network failure degrades to "unconfirmed" (`breach_check_failed: True`), never a false "clean" claim.

~~2. **Self-contained HTML export.**~~ Done — `src/export.py`'s `generate_html()`/`export_to_file()` render score + breakdown + prioritized gaps + remediation history as one static HTML file: inline CSS only, no external fonts/scripts/images/network calls, no secrets (the graph itself never holds any, so there's nothing to redact). All interpolated text is `html.escape()`'d. Wired to a new **Export Report** button on the Dashboard (`ui/dashboard.py`), using a normal save-file dialog. Report chrome text respects the active locale; gap descriptions stay English-only for now, matching `metrics.py`'s existing documented limitation.

The PRD's own MVP scope (`README.md` Roadmap → v1) isn't fully done without this one:

1. **KeePass XML importer.** The PRD's import formats list includes it alongside 1Password/Bitwarden/CSV; only those three exist in `src/importers/`. Same shape as the existing importers — `parse(filepath) -> list[account dict]`, using `_shared.py`'s helpers, including the same breach-check call the other three now make. KeePass XML structure is public and documented; no test fixtures for it exist yet either.

## Medium Priority

2. **Automated test suite.** Every module in this repo has been verified during development with throwaway scripts (drive the code directly, assert, delete the script) — none of that is committed. Worth turning the more valuable of those into a real `pytest` suite under `tests/`, particularly: `store.py`'s encryption round-trip, `graph.py`'s blast-radius/cut-vertex/cycle math, `metrics.py`'s four score components against known scenarios (now including the `"breached"` gap), `remediation.py`'s six `_apply_fix` mutations, `hibp.py`'s k-anonymity matching logic (mock the HTTP call — don't hit the real API from a test suite), and `export.py`'s HTML escaping (a hostile display name or history description must never appear unescaped). Add `pytest` to `requirements.txt` (dev-only) and a CI job that runs it on PRs.
3. **Graph visualization screen.** PRD section 13 calls for this explicitly ("disponible como herramienta de exploración, no como pantalla principal"). The graph and all its query functions (`get_blast_radius`, `get_cut_vertices`, `get_cycles`) already exist — this is purely a new `ui/` frame to render them, no new engine work.
4. **Human QA pass.** Run `QA.md` for real on Windows, macOS, and Linux, with real (throwaway) exports from actual 1Password/Bitwarden accounts — every importer test so far has used hand-built synthetic fixtures in scratch scripts, not a real export file from the real app. Now also covers a real (throwaway, definitely-breached, e.g. "password123") test password to confirm the HIBP check actually flags it end to end, a real offline run (disconnect network) to confirm the "could not check for breaches" message shows instead of a false negative, and opening an exported HTML report in a real browser on each OS.

## Deferred On Purpose

5. **API integrations** (GitHub, Google Workspace, Microsoft Entra) — explicitly pushed to the end per project decision. `ui/onboarding.py`'s "Connect Integration" panel is wired to a "Coming Soon" dialog and nothing else. When this starts: GitHub first (PRD section 7 lists it as the only MVP-scoped integration), needs OAuth or PAT-based auth, a client for 2FA/PAT/SSH-key/session status, and — the reason this is last — a real answer to the PRD's own risk note in section 10: an integration with write scope becomes the graph's highest-blast-radius node.

## Later Phases (PRD)

6. **Drift monitoring** (Roadmap v2) — periodic re-import, change detection, the "you haven't reviewed these 3 critical accounts in 90 days" review session. `metrics.py`'s staleness check (`_is_stale`, `STALE_AFTER_DAYS`) already exists as the underlying signal; this phase is the UI/scheduling layer on top of it. A periodic Pwned Passwords re-check (without re-importing) is a natural companion here, since a password can become breached after the fact.
7. **Published native installers** (Roadmap v4) — `build.spec` and `.github/workflows/build.yml` exist and build successfully locally, but the workflow triggers on a `v*` tag push and no such tag has ever been pushed. First real release is just pushing a tag once the above is far enough along to be worth shipping.
8. **The narrow automated-remediation exception** (PRD section 10: e.g. auto-revoking an expired GitHub PAT) — blocked on #5. Don't build this before there's an actual API client with a real minimal-scope token to revoke.

## Notes for Next Session

- `.venv/` is gitignored and not committed — recreate it (see `README.md` Getting Started) before running anything.
- Delete any `_scratch_*` files or `scratch_*.py` scripts left in the repo root before committing — they're throwaway verification scripts, never meant to ship. None should currently be present, but check.
- `dist/`, `build/`, and `__pycache__/` are gitignored; if a PyInstaller run leaves them around locally, clean them up before diffing.
