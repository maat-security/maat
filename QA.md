# Maat — Manual QA Plan

This is a plan for a human to run through, not an automated suite. Everything below has already been verified with throwaway headless scripts during development (no screenshots — see the note at the bottom on why), but none of that replaces actually looking at the app on a real screen, on each real OS.

Report bugs using the template at the bottom. **Never attach your real vault file, your real passphrase, or a real password manager export to a bug report** — this tool exists specifically to keep that data off other people's servers; don't undo that while reporting a bug about it. Use throwaway test data (see [Test Data](#test-data) below).

## Setup Per OS

### Windows

```powershell
git clone https://github.com/maat-security/maat.git
cd maat
python -m venv .venv
.venv\Scripts\activate
pip install -r requirements.txt
python src\main.py
```

Vault location to check: `%APPDATA%\Maat\`

### macOS

```bash
git clone https://github.com/maat-security/maat.git
cd maat
python3 -m venv .venv
source .venv/bin/activate
pip install -r requirements.txt
python src/main.py
```

Vault location to check: `~/Library/Application Support/Maat/`

### Linux

```bash
git clone https://github.com/maat-security/maat.git
cd maat
python3 -m venv .venv
source .venv/bin/activate
pip install -r requirements.txt
python src/main.py
```

Vault location to check: `~/.local/share/Maat/`

Note which desktop environment and display server (X11 vs Wayland) you're on — CustomTkinter/Tk rendering issues are more likely here than on Windows/macOS.

### PyInstaller Build (all three OSes)

```bash
pip install pyinstaller
pyinstaller build.spec
```

Run the binary from `dist/` directly — don't run it from inside the source checkout with the venv active, since the point is to catch anything that only breaks once bundled (missing data files, path resolution, etc.).

## Test Data

Don't use your real accounts. Options:

- **1Password**: create a free trial or a throwaway vault with 3-5 fake logins (mix of password-only, one with TOTP enabled, one with a passkey if your test device supports it), then export it as 1PUX (Settings → Export → 1Password Unencrypted Export).
- **Bitwarden**: same idea — a throwaway vault, Tools → Export Vault → `.json` (unencrypted). Also create one item and set a password-protected export once, specifically to test that Maat rejects it with a clear error instead of crashing.
- **KeePass**: create a throwaway `.kdbx` database with 3-5 fake entries (mix of password-only, one with a TOTP seed set via KeePass 2.54+'s built-in TOTP or the KeeTrayTOTP plugin), then File → Export → **KeePass XML (2.x)**. Also add one entry, delete it (so it lands in KeePass's own Recycle Bin group), and confirm it does *not* show up after import.
- **Generic CSV**: export from Chrome (`chrome://settings/passwords` → ⋮ → Export passwords) or hand-write a CSV with columns `name,url,password,totp,last_modified`.
- **Questionnaire**: no export needed — just answer with fake account names ("Test Bank", "Test Email").
- **For the Have I Been Pwned check** (any import method): give at least one throwaway fake login a well-known breached password (e.g. `password123`, `qwerty123`) and at least one a long random string you generate yourself — the first should come back flagged, the second should not. Never use a real password you actually use anywhere, even a throwaway account's — the whole point of the k-anonymity design is that Maat doesn't need you to trust it with the real thing.

## Test Cases

### 1. First Launch

- [ ] No vault exists yet → app shows **Create Your Vault**, not Unlock
- [ ] Type a passphrase under 12 characters → inline error, no crash
- [ ] Type two different passphrases in the two fields → "Passphrases do not match.", no crash
- [ ] Type a valid, matching passphrase, click **Create** → lands on Onboarding (graph is empty)
- [ ] Check the vault path for your OS (above) — a `vault.enc` and `vault.salt` file should now exist there
- [ ] Open `vault.enc` in a text editor — it should be unreadable binary, not plaintext

### 2. Unlock

- [ ] Close and relaunch the app → shows **Unlock Your Vault**, not Create
- [ ] Type the wrong passphrase → "Incorrect passphrase.", no crash, still on the unlock screen
- [ ] Type the correct passphrase → lands on Onboarding/Dashboard depending on whether you've added data yet

### 3. Language and Theme (Welcome Screen)

- [ ] Click **ES** → all text on the welcome screen switches to Spanish immediately, no restart needed
- [ ] Click **EN** → switches back
- [ ] Click the dark/light toggle → background and text colors flip, nothing unreadable in either mode
- [ ] After switching language and/or theme, proceed to create/unlock the vault — the choice should carry through to Onboarding and the Dashboard

### 4. Onboarding — Import (repeat once per password manager)

For each of 1Password / Bitwarden / KeePass / generic CSV:

- [ ] Click **Import Password Manager** → **Start** → file picker opens
- [ ] Select your test export → format picker dialog appears with a sensible default guessed from the file extension
- [ ] Click **Import** → button switches to "Importing…" and becomes unclickable while it runs, and the rest of the window stays responsive (drag it around) instead of freezing — this is the Have I Been Pwned network check running in the background
- [ ] Once it finishes: success message shows the account count, and it matches how many items were in your test export
- [ ] Screen switches to the Dashboard automatically once the graph has data
- [ ] The account you gave a known-breached test password (see [Test Data](#test-data)) shows a "password has appeared in a known data breach" gap on the Dashboard; the account with the random password does not
- [ ] Click **Fix This** on the breach gap → Remediation screen shows the "change its password now" runbook; click **I Completed This** → back on the Dashboard, that gap is gone
- [ ] Turn off your network connection, then re-import a fresh test export → import still completes (accounts show up), but the success message also says it couldn't check for breaches — no crash, and nothing gets silently marked as clean
- [ ] Select the **wrong** format on purpose (e.g. pick "Bitwarden" for a 1Password file) → should show a clear inline error, not crash
- [ ] Bitwarden only: try importing a password-protected/encrypted export → clear error telling you to re-export unencrypted, no crash
- [ ] KeePass only: the entry you deleted into the Recycle Bin before exporting does **not** appear among the imported accounts
- [ ] KeePass only: the entry with a TOTP seed set shows up with its TOTP factor recognized (not treated as password-only)

### 5. Onboarding — Answer Questions

- [ ] Click **Answer Questions** → questionnaire opens on question 1/4
- [ ] Fill in an account name and criticality, answer all 4 questions, click through with **Next** each time → last step's button says **Finish**
- [ ] Click **Finish and Return** partway through (after only answering 1-2 questions) → account still gets created with just those answers, no crash
- [ ] Click **Skip** on a question → that question is left blank for this account, wizard still advances
- [ ] Click **Back** after answering a question → previous answer is still there, editable
- [ ] After finishing, Dashboard shows this account reflected in the score/gaps

### 6. Dashboard

- [ ] With at least one imported/answered account, score shows as `NN/100`, never just a bare number with no context
- [ ] All four component rows are visible with their plain-language one-line explanation
- [ ] If you set up a scenario matching the PRD example (passkey auth + SMS recovery, or a mutual email/phone recovery cycle, or a lone TOTP factor with no backup) — confirm the matching gap shows up in the list, in plain language, with no metric names or raw numbers
- [ ] Click **Fix This** on any gap → Remediation screen opens showing that gap's specific runbook
- [ ] Click **Add More Data** → returns to Onboarding, previously entered data is untouched
- [ ] Click **Export Report** → save-file dialog opens, defaulting to a `.html` filename → save it somewhere → status message says the report was saved
- [ ] Open that `.html` file directly in a real browser (double-click it, no app running) → renders correctly with no broken layout, and the score/gaps/history match what the Dashboard showed
- [ ] Open the exported file's page source / view-source → confirm there's no `<script>` tag, no `http://` or `https://` reference of any kind (no external fonts, images, or calls out) — this file must work fully offline forever
- [ ] Skim the file for anything that looks like a real password, TOTP secret, or recovery code — there should be nothing beyond account names, URLs, and the same plain-language gap text already on the Dashboard

### 7. Remediation

- [ ] The before/after numbers shown make sense relative to what's on the Dashboard (i.e. "after" should be ≤ "before")
- [ ] For a `recovery_asymmetry` or `cycle` gap, the sequencing warning is visible and makes sense
- [ ] If a deep link button is shown, clicking it opens your **actual default browser** to the real settings page for that provider (only testable if the account's URL matched a recognized provider — google.com, github.com, microsoft.com/outlook.com/live.com, apple.com/icloud.com)
- [ ] Click **Not Now** → returns to Dashboard, nothing changed
- [ ] Click **I Completed This** → returns to Dashboard, score/gaps recalculated, and a "Recently Completed" line appears with today's date

### 8. Connect Integration

- [ ] Click **Connect Integration** → **Start** → shows "Coming Soon", does not crash or pretend to connect to anything

### 9. Cross-Platform Specifics

- [ ] Window renders at a reasonable size on first launch on this OS — nothing cut off, no overlapping text
- [ ] Try a non-100% display scale factor if your OS/monitor supports it (125%, 150%) — same check
- [ ] Native window chrome (title bar, close/minimize buttons) looks like a normal app on this OS, not visually broken
- [ ] The vault path from [Setup Per OS](#setup-per-os) is exactly where the files landed — no fallback path was silently used

## What NOT to Report as a Bug

These are known, already-documented gaps (see `README.md`'s Implementation Status section) — please don't file issues for these unless you're seeing something *worse* than "it doesn't exist yet":

- Any graph visualization screen (not built)
- Connect Integration doing anything beyond "Coming Soon"
- Anything related to a published installer or `pip install maat` — there isn't one yet

## Bug Report Template

```
OS + version:
Python version (or: PyInstaller binary, version/commit):
Display scaling (100% / 125% / other):
Steps to reproduce:
Expected:
Actual:
Screenshot (if visual) — crop out any real account names/URLs:
```

## Why This Is a Manual Plan, Not an Automated One

Everything in this repo has been verified during development with throwaway Python scripts that drove the UI programmatically (calling widget methods directly, not clicking at screen coordinates) and asserted on the results, then deleted themselves — not screenshots. Coordinate-based click automation turned out to be unreliable in the sandboxed environment used to build this (window positions reported by the OS didn't match what was actually on screen), so verification shifted to driving the code directly instead of the pixels. That's real verification of behavior, but it is not the same as a person looking at rendered text on a real monitor, which is what this document is for.

There **is** now a committed `pytest` suite under `tests/` (111 tests, run on every push/PR — see `TODO.md`), covering the engine, scoring, remediation, importers, HIBP client, and HTML export. It's a real safety net against regressions, but it deliberately doesn't touch `ui/` or `main.py` at all — no Tk widgets are instantiated, no display/window server is required, so it runs headless in CI on all three OSes. That's exactly the gap this manual plan exists to cover: nothing in `tests/` will ever catch a rendering glitch, an unreadable color combination, or a display-scaling issue, because it never looks at a screen.
