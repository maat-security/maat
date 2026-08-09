"""Guided remediation — never automatic.

The product's own risk model says an agent with write credentials over
every account becomes the graph's highest-blast-radius node. So this
module never calls out to any provider's API to change anything. What
it does:

  - get_runbook(): ordered, provider-aware steps + a deep link the user
    follows themselves, plus a sequencing warning where order matters.
  - simulate_fix(): a before/after estimate of the graph's worst-case
    exposure if the gap were fixed, computed on a throwaway copy.
  - mark_gap_resolved(): once the user says they did it, updates
    Maat's own model of the graph to match (self-reported, so
    confidence stays "declared" — there's no API to verify it against
    yet) and records the completion with a timestamp.

The narrow future exception the PRD carves out — automating writes
only where the API is minimal-scope and non-destructive in the wrong
direction (e.g. revoking an expired GitHub PAT) — isn't implemented
here. No integration exists yet to automate anything through.
"""

import datetime
import json

import networkx as nx

import graph as graph_module
import metrics
import store

HISTORY_KEY = "remediation_history"

GENERIC_RUNBOOKS = {
    "phishing_vulnerable": {
        "steps": [
            "Open this account's security settings.",
            'Look for "Passkeys", "Security keys", or "Two-factor authentication".',
            "Add a passkey or hardware security key if the option is offered.",
        ],
        "deep_link": None,
    },
    "recovery_asymmetry": {
        "steps": [
            "Open this account's account-recovery settings.",
            "Add or confirm a stronger recovery method (an authenticator app or passkey) first.",
            "Remove the weaker recovery channel (e.g. SMS) once the stronger one is active.",
        ],
        "deep_link": None,
    },
    "cycle": {
        "steps": [
            'Pick one of the two accounts to be the "recovery anchor".',
            "On the other account, remove its recovery relationship back to the anchor.",
            "Confirm the anchor account still has its own independent recovery path.",
        ],
        "deep_link": None,
    },
    "orphaned_factor": {
        "steps": [
            "Open this account's two-factor / backup settings.",
            "Generate backup or recovery codes.",
            "Store them somewhere durable and separate from the device this factor lives on.",
        ],
        "deep_link": None,
    },
    "cut_vertex": {
        "steps": [
            "Identify which accounts depend only on this device or factor.",
            "Add an independent authentication method — a second hardware key, or a "
            "passkey on a different device — to at least one of them.",
            "Consider a backup device or key as a fallback for this one.",
        ],
        "deep_link": None,
    },
}

SEQUENCE_WARNINGS = {
    "recovery_asymmetry": (
        "Set up the stronger recovery method first — removing the weak one before "
        "that risks locking yourself out."
    ),
    "cycle": (
        "Breaking this cycle removes one direction of recovery. Make sure the "
        "account you keep as the anchor has its own independent recovery path."
    ),
}

# Real, well-known settings URLs — never a guess or a placeholder. A
# provider not listed here gets the generic runbook, not a fabricated link.
PROVIDER_RUNBOOKS = {
    "google": {
        "deep_link": "https://myaccount.google.com/security",
        "phishing_vulnerable": {
            "steps": [
                "Go to myaccount.google.com/security.",
                'Under "How you sign in to Google", select "Passkeys and security keys".',
                "Add a passkey using your device or a hardware key.",
            ],
        },
        "recovery_asymmetry": {
            "steps": [
                "Go to myaccount.google.com/security.",
                'Under "How you can recover your account", review your recovery phone and email.',
                "Remove the SMS recovery option only after confirming a passkey or "
                "authenticator app is active.",
            ],
        },
        "orphaned_factor": {
            "steps": [
                "Go to myaccount.google.com/security.",
                "Add a backup phone number or download backup codes.",
                "Store backup codes somewhere durable, separate from this device.",
            ],
        },
    },
    "github": {
        "deep_link": "https://github.com/settings/security",
        "phishing_vulnerable": {
            "steps": [
                "Go to github.com/settings/security.",
                'Under "Passkeys", click "Add a passkey".',
                "Follow your browser or OS prompt to register it.",
            ],
        },
        "orphaned_factor": {
            "steps": [
                "Go to github.com/settings/security.",
                'Under "Two-factor authentication", download and store your recovery codes.',
                "Consider adding a hardware security key as a second method.",
            ],
        },
    },
    "microsoft": {
        "deep_link": "https://mysignins.microsoft.com/security-info",
        "phishing_vulnerable": {
            "steps": [
                "Go to mysignins.microsoft.com/security-info.",
                'Click "Add sign-in method" and choose "Security key" or "Passkey".',
                "Follow the prompt to register it.",
            ],
        },
    },
    "apple": {
        "deep_link": None,
        "phishing_vulnerable": {
            "steps": [
                "Open Settings on your iPhone, iPad, or Mac.",
                'Go to your Apple ID, then "Sign-In & Security".',
                'Select "Passkeys" and follow the prompt to add one.',
            ],
        },
    },
}

PROVIDER_DOMAIN_HINTS = {
    "google": ("google.com", "gmail.com"),
    "github": ("github.com",),
    "microsoft": ("microsoft.com", "outlook.com", "live.com", "hotmail.com"),
    "apple": ("apple.com", "icloud.com"),
}


def detect_provider(url) -> str:
    """Match a URL against known providers by domain substring. Returns
    "generic" for anything unrecognized or missing — never a guess."""
    if not url:
        return "generic"
    lowered = str(url).lower()
    for provider, hints in PROVIDER_DOMAIN_HINTS.items():
        if any(hint in lowered for hint in hints):
            return provider
    return "generic"


def get_runbook(g: nx.DiGraph, gap: dict) -> dict:
    """Return {"steps": [...], "deep_link": str | None, "sequence_warning":
    str | None} for this gap — provider-specific if the affected
    identity's url matches one Maat recognizes, generic otherwise."""
    kind = gap["kind"]
    node = gap["node"]
    identity_node = node if isinstance(node, str) else (node[0] if node else None)

    url = None
    if identity_node is not None and identity_node in g:
        url = g.nodes[identity_node].get("url")

    provider = detect_provider(url)
    provider_entry = PROVIDER_RUNBOOKS.get(provider, {})
    specific = provider_entry.get(kind)

    if specific:
        steps = specific["steps"]
        deep_link = provider_entry.get("deep_link")
    else:
        generic = GENERIC_RUNBOOKS.get(kind, {"steps": [], "deep_link": None})
        steps = generic["steps"]
        deep_link = generic["deep_link"]

    return {
        "steps": steps,
        "deep_link": deep_link,
        "sequence_warning": SEQUENCE_WARNINGS.get(kind),
    }


def simulate_fix(g: nx.DiGraph, gap: dict) -> dict:
    """Return {"before_exposed": int, "after_exposed": int} — the whole
    graph's worst-case exposure before and after hypothetically
    applying this gap's fix. Operates on a copy; never mutates g."""
    before = metrics.worst_case_exposure(g)
    working_copy = g.copy()
    _apply_fix(working_copy, gap)
    after = metrics.worst_case_exposure(working_copy)
    return {"before_exposed": before, "after_exposed": after}


def mark_gap_resolved(g: nx.DiGraph, gap: dict) -> dict:
    """Apply this gap's fix to the live graph and record completion in
    the encrypted store. Returns the completion record.

    This updates Maat's model to match what the user just told it they
    did — it does not itself change anything on any provider's site.
    """
    _apply_fix(g, gap)
    record = {
        "kind": gap["kind"],
        "node": gap["node"] if isinstance(gap["node"], str) else list(gap["node"]),
        "description": gap["description"],
        "completed_at": _now_iso(),
    }
    history = get_completed_history()
    history.append(record)
    store.store_set(HISTORY_KEY, json.dumps(history))
    return record


def get_completed_history() -> list:
    """Return previously completed remediations, most recent last."""
    raw = store.store_get(HISTORY_KEY)
    if not raw:
        return []
    try:
        return json.loads(raw)
    except (TypeError, ValueError):
        return []


def _now_iso() -> str:
    return datetime.datetime.now(datetime.timezone.utc).isoformat()


# --------------------------------------------------------------------------
# Fix mutations — one per gap kind, shared by simulate_fix() (on a copy)
# and mark_gap_resolved() (on the live graph).
# --------------------------------------------------------------------------

def _apply_fix(g: nx.DiGraph, gap: dict) -> None:
    kind = gap["kind"]
    node = gap["node"]

    if kind == "phishing_vulnerable":
        _apply_phishing_fix(g, node)
    elif kind == "recovery_asymmetry":
        _apply_recovery_asymmetry_fix(g, node)
    elif kind == "cycle":
        _apply_cycle_fix(g, node)
    elif kind == "orphaned_factor":
        _apply_orphaned_factor_fix(g, node)
    elif kind == "cut_vertex":
        _apply_cut_vertex_fix(g, node)


def _apply_phishing_fix(g: nx.DiGraph, identity: str) -> None:
    """Strengthen the identity's best existing factor to a passkey, or
    add one if it has none."""
    now = _now_iso()
    factors = [
        u for u, _, d in g.in_edges(identity, data=True)
        if d.get("type") == "AUTHENTICATES" and g.nodes[u].get("type") == "Factor"
    ]
    if factors:
        best = max(factors, key=lambda f: graph_module.factor_resistance_rank(g.nodes[f].get("kind", "")))
        g.nodes[best]["kind"] = "passkey"
        g.nodes[best]["confidence"] = "declared"
        g.nodes[best]["last_verified"] = now
    else:
        factor_id = f"{identity}::factor"
        g.add_node(factor_id, type="Factor", kind="passkey", confidence="declared", last_verified=now)
        g.add_edge(factor_id, identity, type="AUTHENTICATES")
    if identity in g:
        g.nodes[identity]["last_verified"] = now


def _apply_recovery_asymmetry_fix(g: nx.DiGraph, identity: str) -> None:
    """Remove whichever recovery paths are weaker than the identity's
    strongest sign-in factor — mirrors metrics._compute_recovery_hygiene's
    own asymmetry test exactly, so a fix here is a real fix there."""
    now = _now_iso()
    auth_factors = [
        u for u, _, d in g.in_edges(identity, data=True)
        if d.get("type") == "AUTHENTICATES" and g.nodes[u].get("type") == "Factor"
    ]
    auth_rank = max(
        (graph_module.factor_resistance_rank(g.nodes[f].get("kind", "")) for f in auth_factors),
        default=0,
    )
    recovery_nodes = [u for u, _, d in g.in_edges(identity, data=True) if d.get("type") == "RECOVERS"]
    for r in recovery_nodes:
        recovery_rank = (
            graph_module.factor_resistance_rank(g.nodes[r].get("kind", ""))
            if g.nodes[r].get("type") == "Factor"
            else 0
        )
        if auth_rank > recovery_rank and g.has_edge(r, identity):
            g.remove_edge(r, identity)
    if identity in g:
        g.nodes[identity]["last_verified"] = now


def _apply_cycle_fix(g: nx.DiGraph, cycle) -> None:
    """Break the cycle by removing one edge in it — enough to make it
    no longer mutual."""
    nodes = list(cycle)
    if len(nodes) < 2:
        return
    now = _now_iso()
    if g.has_edge(nodes[-1], nodes[0]):
        g.remove_edge(nodes[-1], nodes[0])
    elif g.has_edge(nodes[0], nodes[1]):
        g.remove_edge(nodes[0], nodes[1])
    for n in nodes:
        if n in g:
            g.nodes[n]["last_verified"] = now


def _apply_orphaned_factor_fix(g: nx.DiGraph, identity: str) -> None:
    """Add a backup recovery channel — the identity is no longer a
    single factor with no way back in."""
    now = _now_iso()
    recovery_id = f"{identity}::backup-recovery"
    if recovery_id not in g:
        g.add_node(recovery_id, type="RecoveryChannel", kind="recovery_codes", confidence="declared", last_verified=now)
    g.add_edge(recovery_id, identity, type="RECOVERS")
    if identity in g:
        g.nodes[identity]["last_verified"] = now


def _apply_cut_vertex_fix(g: nx.DiGraph, node: str) -> None:
    """Add a parallel backup node carrying the same outgoing edges, so
    this node is no longer the *only* bridge to what it reaches."""
    now = _now_iso()
    backup_id = f"{node}::backup"
    if backup_id not in g:
        g.add_node(
            backup_id,
            type=g.nodes[node].get("type", "Device"),
            confidence="declared",
            display_name=f"Backup for {g.nodes[node].get('display_name', node)}",
            last_verified=now,
        )
    for _, target, data in list(g.out_edges(node, data=True)):
        g.add_edge(backup_id, target, **data)
    if node in g:
        g.nodes[node]["last_verified"] = now
