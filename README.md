# Maat 🪶

Your identity, in balance.

![License: MIT](https://img.shields.io/badge/License-MIT-C9A84C.svg)
![By Heru](https://img.shields.io/badge/by-Heru-2D2D2D.svg)
![Status: Pre-Alpha](https://img.shields.io/badge/status-pre--alpha-555555.svg)

🌐 Also available in: [Español](README.es.md)

An open source project by Heru · heru.life · MIT License

## Table of Contents

- [The Problem No One Is Solving](#the-problem-no-one-is-solving)
- [What Maat Does](#what-maat-does)
- [How You Get Started](#how-you-get-started)
- [Getting Started](#getting-started)
- [What It Never Does](#what-it-never-does)
- [Design Principle: Local-First, No Exceptions](#design-principle-local-first-no-exceptions)
- [SIM Swap Is in the Model](#sim-swap-is-in-the-model)
- [Roadmap](#roadmap)
- [Implementation Status](#implementation-status)
- [Contributing](#contributing)
- [Security](#security)
- [About](#about)

## The Problem No One Is Solving

You manage zero-trust policies at work. You review access logs. You know what a blast radius is.

And your personal Gmail recovers via SMS to the same phone where your TOTP app lives.

Every security tool built for personal use evaluates accounts in isolation. Password managers flag weak passwords. Have I Been Pwned tells you if your email appeared in a breach. None of them answer the only question that matters:

If an attacker compromises one account, how much falls with it?

Recovery channels are the real attack surface. Account recovery exists precisely to bypass authentication. A user with a passkey on Gmail and an SMS recovery phone number has, in practice, SMS-level security. The back door is weaker than the front door, and no tool is showing you that.

## What Maat Does

Maat maps your digital identity as a dependency graph — every account, authentication factor, device, recovery channel, and provider, and every relationship between them.

From that map, it tells you what actually matters:

- "If your phone is stolen, these 6 accounts are immediately at risk."
- "Your email and your phone protect each other. If you lose one, you lose both."
- "Your GitHub TOTP has no backup. If you lose your phone, you lose access permanently."
- "Your bank has strong authentication, but it can be recovered by SMS. In practice, it has SMS-level security."

Then it gives you a prioritized list of actions, ordered by how many accounts you protect with each fix. The graph is the engine. Consequences are the interface.

## How You Get Started

There is no required path. Start with whatever you have:

- Import your password manager export — brings in your full account inventory in minutes.
- Answer questions about your accounts — walk through how you authenticate and how you'd recover access if you lost your primary factor.
- Connect an integration — GitHub and others read your security configuration directly via API.

Use one. Use all three. Do them in any order. Maat builds your picture from whatever you provide and shows you results immediately — there is no "setup complete" gate before you get value.

## Getting Started

> **Pre-alpha.** Not published as a package or a binary yet — run it from source.

```bash
git clone https://github.com/maat-security/maat.git
cd maat
python -m venv .venv
.venv\Scripts\activate      # macOS/Linux: source .venv/bin/activate
pip install -r requirements.txt
python src/main.py
```

The app itself walks you through the three optional onboarding paths — import a password manager export, answer the guided questionnaire, or connect an integration (not built yet; see [Implementation Status](#implementation-status)). Use one, use all three, in any order.

`pip install maat` and prebuilt native binaries are the v1/v4 goals in the [Roadmap](#roadmap) below, not something you can do today.

## What It Never Does

- Store passwords, TOTP seeds, or recovery codes.
- Send any data anywhere. No telemetry, no backend, no account required.
- Execute changes on your behalf.
- Leave an unencrypted file on disk.

## Design Principle: Local-First, No Exceptions

The file Maat produces is the complete map of your digital identity. Storing it in the cloud would create exactly the single point of failure the tool exists to eliminate. Everything runs on your machine. The only outbound calls are Have I Been Pwned (k-anonymity, your password hashes never leave your device) and the provider integrations you explicitly connect.

## SIM Swap Is in the Model

Your mobile carrier can be SIM-swapped. Maat models this and shows you which accounts are exposed if your number is ported without your consent. The remediations are real and actionable: carrier-level number lock, eSIM migration, or removing phone-based recovery from critical accounts.

## Roadmap

- **v1 — MVP:** Password manager import, HIBP check, guided questionnaire, dependency map, posture score, prioritized action list, local encrypted store.
- **v2 — Drift monitoring:** Periodic re-import, change detection, lightweight review sessions.
- **v3 — Guided remediation:** Provider-specific runbooks with sequencing warnings, pre/post simulation, API-based verification.
- **v4 — Desktop apps:** Native installers for Windows, macOS, and Linux. Same engine, no terminal required.

## Implementation Status

_Last updated 2026-08-09._ What's real and running today, versus what's still on the roadmap above.

**Working now:**

- Encrypted local vault — passphrase-derived key, no plaintext ever written to disk
- Dependency graph engine — node/edge validation, blast radius, cut vertices, cycle detection
- Posture scoring — the four weighted components from the product spec, with an auditable breakdown
- Guided questionnaire — four skippable questions per account, state-machine driven
- Password manager import — 1Password (`.1pux`), Bitwarden (JSON), generic CSV — with in-memory password-reuse detection and a Have I Been Pwned breach check, neither of which ever persists a password value
- Have I Been Pwned integration — k-anonymity Pwned Passwords check (only a 5-character hash prefix ever leaves the device), run in a background thread during import, surfaced as a prioritized "this password is breached" gap with its own remediation runbook
- Guided remediation — provider-aware runbooks (Google, GitHub, Microsoft, Apple, honest generic fallback otherwise), before/after impact simulation, self-reported completion history
- Bilingual UI (English/Spanish) and a dark/light theme toggle
- Desktop shell (CustomTkinter) with a PyInstaller packaging spec and a three-OS CI build workflow

**Known gaps:**

- KeePass XML import isn't built — only 1Password, Bitwarden, and generic CSV today
- No graph visualization screen — the graph exists and is queried, but there's nothing to look at yet
- No committed automated test suite — everything above has been verified with throwaway scripts during development, not a checked-in `pytest` suite

**Not started:**

- Self-contained HTML export
- Any provider API integration (GitHub, Google Workspace, Microsoft Entra) — deferred on purpose, in favor of finishing the local-first core first
- Drift monitoring / periodic review sessions (Roadmap v2)
- Published native installers (Roadmap v4) — the CI workflow exists but has never been triggered by a real release tag
- The narrow automated-remediation exception for minimal-scope, non-destructive API writes (e.g. revoking an expired GitHub PAT) — blocked on the integration point above

See [TODO.md](TODO.md) for the prioritized next-work list, and [QA.md](QA.md) for the manual test plan covering Windows, macOS, and Linux.

## Contributing

**Bugs.** Report them as GitHub Issues.

**Pull requests.** Fork the repo, branch off `main`, open a PR against `main`.

**Translations.** `/docs/en` is the source of truth. Translations go in `/docs/{locale}`. A PR adding or updating a translation requires review from a native speaker of that language before merge.

Code and issues are in English. `/docs/es` is the exception — it's officially maintained in Spanish by the core team, not community-translated.

## Security

Security issues must be reported privately to alvartorres@heru.life. Do not open public GitHub issues for security vulnerabilities.

## About

Maat is an open source project donated to the security community by Heru (heru.life). Named after the Egyptian goddess of truth, justice, and balance — whose feather was the standard against which the heart was weighed. If the heart was heavier than the feather, there was imbalance. That's what Maat finds. MIT License.
