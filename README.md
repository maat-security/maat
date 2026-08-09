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

> **Pre-alpha.** The install path and CLI below are placeholders for the v1 MVP. Nothing here is published yet.

Install (planned):

```bash
pip install maat
```

Run onboarding using any of the three optional paths — independently or combined:

```bash
# Path 1: import your password manager export
maat import --source 1password export.1pux

# Path 2: answer the guided questionnaire
maat questionnaire

# Path 3: connect an integration
maat connect github
```

Then view your posture score and prioritized actions:

```bash
maat status
```

This is coming in v1. Maat is pre-alpha — there is no installable release yet.

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

## Contributing

**Bugs.** Report them as GitHub Issues.

**Pull requests.** Fork the repo, branch off `main`, open a PR against `main`.

**Translations.** `/docs/en` is the source of truth. Translations go in `/docs/{locale}`. A PR adding or updating a translation requires review from a native speaker of that language before merge.

Code and issues are in English. `/docs/es` is the exception — it's officially maintained in Spanish by the core team, not community-translated.

## Security

Security issues must be reported privately to alvartorres@heru.life. Do not open public GitHub issues for security vulnerabilities.

## About

Maat is an open source project donated to the security community by Heru (heru.life). Named after the Egyptian goddess of truth, justice, and balance — whose feather was the standard against which the heart was weighed. If the heart was heavier than the feather, there was imbalance. That's what Maat finds. MIT License.
