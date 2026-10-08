"""Stateless-inference residual reconstruction — the insider's view (P14).

A provider that advertises "stateless inference" means *no chat history as a
product feature*, not *zero residual data*. Eight independent surfaces still
carry pieces of every request: observability logs, token billing, vector
stores, caches, training/eval staging, infrastructure leftovers, human
support tooling, and the amplifier that ties them together — repeated
near-queries.

This module models each surface as a **retention policy** applied to every
ingested prompt, then measures how much of the registered ground truth an
insider holding a given *set* of surfaces can reassemble:

- each surface alone (what that store gives away in isolation),
- a growing prefix of surfaces (marginal contribution, monotone by
  construction — the text pool only ever grows),
- per-request vs pooled (what repetition amplification buys).

Honesty rules carried over from P8: values are synthetic and drawn from
reserved documentation ranges; pure vector-only inversion is NOT claimed —
the embeddings surface stores vectors and measures *linkage* (how few
near-dup families the user's traffic collapses into), and reports 0 accuracy
until some text-bearing surface is added alongside it.
"""
from __future__ import annotations

import hashlib
import re
import threading

from . import analysis
from . import attacks
from . import embeddings as emb_mod
from . import queries
from . import sensitive
from . import harvest as harvest_mod

HEAD_CHARS = 180      # structured logging keeps a prompt head
TRACE_CHARS = 120     # distributed-tracing payload capture
FRAG_CHARS = 90       # an employee pastes a window around the secret
PREFIX_MIN = 24       # shared prefix short enough to be a cache key, not content

EMBED_DIM = 384

# Sample rates are deterministic fractions of turns (stable across runs and
# processes — no RNG state). They encode "how often this store keeps the
# full text" as an operational fact, not a random draw. They are deliberately
# modest: a store that kept *every* prompt would make the per-surface
# gradient flat, and the whole point is measuring how much each one gives
# away on its own.
RATE = {
    "logging_flagged": 0.15,     # safety/moderation sampling to human review
    "billing_dispute": 0.09,     # sampled full prompts for billing disputes
    "training_eval": 0.14,       # offline eval / red-team sampling
    "training_staging": 0.08,    # pre-deletion staging window
    "infra_queue": 0.16,         # message retained beyond the expected TTL
    "infra_snapshot": 0.07,      # object-store version / backup
    "ops_view": 0.12,            # support tool exposes the recent turn
    "ops_paste": 0.05,           # employee pastes the raw value in chat
    "session_resend": 0.30,      # user re-sends the previous message verbatim
}

RESPONSES = [
    "Recorded. I will fold that into the next summary for you.",
    "Understood — noted for this session, nothing else needed.",
    "Thanks, that is consistent with what I already have on file.",
]

DISTRACTORS = [
    "What are the weekend opening hours for the support desk?",
    "Explain the difference between a prefix cache and a response cache "
    "in two sentences.",
    "How do I reset my workspace layout to the default panel arrangement?",
    "Show me how to format a date column so it sorts correctly.",
]

# Partial transaction-set pools for inter-bank aux scenarios. Fixed lists
# sampled by deterministic fractions — synthetic names, no real rails.
_PEER_BANKS = ["Meridian Trust", "First Continental", "Harbor Mutual",
               "Union Pacific Bank", "Crown Sterling", "Northgate Savings"]
_MERCHANTS = ["Aurora Grocers", "Beacon Fuel", "Copperline Air",
              "Driftwood Books", "Ember Electronics", "Foxglove Pharmacy",
              "Granite Hardware", "Halcyon Hotels"]

SURFACES = [
    {"id": "logging", "n": 1, "role": "store",
     "title": "Explicit logging & observability",
     "retains": "prompt heads for every request, full prompt when the safety "
                "or error sampler flags it, completion text",
     "retention": "minutes–days while debugging; longer once flagged",
     "independence": "high — owned by the platform/observability team, "
                     "outside the retention policy the product advertises",
     "diagram": (
         "flowchart TB\n"
         '    P["prompt"] --> H["prompt head<br/>first 180 chars · always<br/>loses a trailing secret"]\n'
         '    P --> F["flagged? sampler<br/>15% of turns"]\n'
         '    F -->|"yes"| FULL["full prompt<br/>sent to review"]\n'
         '    F -->|"no"| D["discarded after window"]\n'
         '    H --> R["insider read"]\n'
         '    FULL --> R\n')},
    {"id": "billing", "n": 2, "role": "store",
     "title": "Token billing & usage metering",
     "retains": "input/output token counts, byte length, prompt SHA-256 for "
                "every request; the full prompt only when a dispute sample "
                "is taken",
     "retention": "invoice lifetime — months, outlives the prompt policy",
     "independence": "high — finance systems are never covered by an "
                     "inference-retention claim",
     "diagram": (
         "flowchart TB\n"
         '    P["prompt"] --> M["meter:<br/>tokens · bytes · sha256"]\n'
         '    P --> S["dispute sampler<br/>9% of turns"]\n'
         '    S -->|"yes"| F["full prompt<br/>held for the invoice window"]\n'
         '    M --> N["metadata only<br/>narrows candidates"]\n'
         '    F --> R["insider read"]\n')},
    {"id": "embeddings", "n": 3, "role": "linker",
     "title": "Vector embeddings & retrieval infrastructure",
     "retains": "a 384-d query vector per request (semantic cache, RAG, "
                "duplicate detection, analytics)",
     "retention": "as long as the index lives — often forever",
     "independence": "high — stored in a different system with a different "
                     "owner than the gateway log",
     "diagram": (
         "flowchart TB\n"
         '    P["prompt"] --> E["embed<br/>384-d vector"]\n'
         '    E --> V[(vector store)]\n'
         '    V --> L["near-dup families<br/>links turns together"]\n'
         '    V --> I["inversion<br/>NOT claimed here"]\n'
         '    L --> R["insider read<br/>accuracy 0 alone"]\n')},
    {"id": "cache", "n": 4, "role": "store",
     "title": "Caching layers",
     "retains": "exact prompt on a repeat hit, the shared prefix on a prefix "
                "hit, and the newest KV snapshot while it lingers in memory",
     "retention": "seconds–hours of wall time, but a snapshot outlives it",
     "independence": "medium — same host as the gateway, short nominal TTL",
     "diagram": (
         "flowchart TB\n"
         '    P["prompt"] --> C{"seen before<br/>or shares a prefix?"}\n'
         '    C -->|"exact"| H["cache hit<br/>full prompt"]\n'
         '    C -->|"prefix ≥24"| PR["shared prefix"]\n'
         '    C -->|"miss"| K["KV snapshot of the<br/>newest turn"]\n'
         '    H --> R["insider read"]\n    PR --> R\n    K --> R\n')},
    {"id": "training", "n": 5, "role": "store",
     "title": "Training & evaluation pipelines",
     "retains": "full prompts sampled for offline eval/red-teaming, plus "
                "rows still sitting in the staging table before the "
                "deletion job runs",
     "retention": "days–30+ days (legal hold), even with opt-out",
     "independence": "high — a separate pipeline with its own copy of the row",
     "diagram": (
         "flowchart TB\n"
         '    P["prompt"] --> SM["eval sampler<br/>14% of turns"]\n'
         '    P --> ST["staging table<br/>8% of turns"]\n'
         '    SM --> T["offline eval set"]\n'
         '    ST --> D["deletion job<br/>runs later"]\n'
         '    T --> R["insider read"]\n'
         '    D -.->|"window still open"| R\n')},
    {"id": "infrastructure", "n": 6, "role": "store",
     "title": "Infrastructure & side residuals",
     "retains": "trace payload heads on every request, whole messages "
                "lingering in a queue, and object-storage snapshot versions",
     "retention": "queue TTL + backup retention — both outlive the prompt",
     "independence": "very high — three different systems, three owners",
     "diagram": (
         "flowchart TB\n"
         '    P["prompt"] --> TR["trace payload<br/>first 120 chars"]\n'
         '    P --> Q["queue buffer<br/>16% of turns"]\n'
         '    P --> O["object snapshot<br/>7% of turns"]\n'
         '    TR --> R["insider read"]\n    Q --> R\n    O --> R\n')},
    {"id": "human_ops", "n": 7, "role": "store",
     "title": "Human & operational access paths",
     "retains": "the window an employee views in a support tool, and — when "
                "someone pastes it into chat while debugging — the BARE "
                "value, not the mask",
     "retention": "forever: chat history and ticket notes are never pruned "
                  "by an inference-retention policy",
     "independence": "very high — a person, not a pipeline",
     "diagram": (
         "flowchart TB\n"
         '    P["prompt"] --> V["support tool view<br/>12% of turns"]\n'
         '    P -->|"value substituted"| PB["paste into chat<br/>5% of turns"]\n'
         '    V --> FR["window around the secret"]\n'
         '    PB --> BR["BARE value in a human transcript"]\n'
         '    FR --> R["insider read"]\n    BR --> R\n')},
    {"id": "amplification", "n": 8, "role": "analysis",
     "title": "Progressive / repeated near-query amplification",
     "retains": "nothing — it is the analysis that pools every selected "
                "surface across every turn and assembles fragments "
                "position-wise",
     "retention": "n/a",
     "independence": "n/a — it multiplies whatever the other seven hold",
     "diagram": (
         "flowchart TB\n"
         '    Q1["turn 1: ***-**-6789"] --> A["pool + cluster<br/>by shape"]\n'
         '    Q2["turn 2: 123-**-****"] --> A\n'
         '    Q3["turn n: paraphrase"] --> A\n'
         '    A --> M["position-wise merge<br/>known chars win"]\n'
         '    M --> S["full value"]\n')},
]

STORE_IDS = [s["id"] for s in SURFACES if s["role"] != "analysis"]
ALL_IDS = [s["id"] for s in SURFACES]

SCENARIOS = {
    "stateless_chat": {
        "title": "Stateless health chat",
        "blurb": "Long checkup questions against a provider that keeps no "
                 "history — SSN and blood-pressure readings still land in "
                 "six other systems.",
        "fields": ["ssn", "bp"],
        "carriers": [
            "I have been recording my readings every morning for the last "
            "six weeks and my cardiologist wants a written summary before "
            "the next appointment. Please describe the overall pattern, "
            "call out anything outside the usual range, and note which "
            "measurements moved after I started the new medication.",
            "Could you explain what the last two results mean in plain "
            "language, and whether the change is large enough that I should "
            "book an earlier appointment? I would also like a short "
            "paragraph I can paste into the patient portal message box "
            "without it sounding alarming.",
            "I am preparing a question list for my GP and I would like you "
            "to rank these concerns by how urgent they sound, keeping in "
            "mind that I am over sixty and have a family history of the "
            "condition we discussed last month.",
        ],
    },
    "stateless_coding": {
        "title": "Stateless coding assistant",
        "blurb": "Debug sessions where the credential sits at the end of a "
                 "long prompt: API key and database password leak into "
                 "logs, meters, caches and snapshots.",
        "fields": ["api_key", "db_password"],
        "carriers": [
            "I am wiring the billing service into our staging cluster and "
            "the integration test keeps failing at the handshake step. The "
            "gateway returns 401 even though the credential is set in the "
            "environment file, and I have already restarted the pod three "
            "times so it picks up the new variables. What else usually "
            "causes this?",
            "Our nightly export job started failing after the platform team "
            "rotated the connection settings. The logs show an "
            "authentication error, but the runbook only mentions checking "
            "the secret store. Walk me through the steps you would take, in "
            "order, and tell me which file to update first.",
            "I need to hand this service over to a colleague next week and "
            "I want the setup notes complete enough that they can reproduce "
            "the environment without asking me follow-up questions. Include "
            "the endpoint, the region, and the reference identifier we use "
            "for this account.",
        ],
    },
    "stateless_support": {
        "title": "Stateless support desk",
        "blurb": "Order and refund threads where the customer repeats their "
                 "contact details — email and callback number end up in "
                 "tickets, traces and chat history.",
        "fields": ["email", "phone"],
        "carriers": [
            "My order still shows as pending three days after the payment "
            "was taken, and the tracking page has not updated since the "
            "label was created. I have already tried the self-service form "
            "twice. Can you tell me what happens next and how long I should "
            "wait before escalating this to a human agent?",
            "I need to change the delivery address because I am moving this "
            "weekend, and the parcel has not shipped yet. The order was "
            "placed through the business account, so please confirm whether "
            "the change is still allowed after payment capture and whether "
            "it changes the dispatch date.",
            "Please send the callback confirmation to the address on file "
            "and let me know whether the refund will go back to the "
            "original payment method or as account credit. I would prefer "
            "the original method if that is still possible at this stage.",
        ],
    },
    "stateless_finance": {
        "title": "Stateless finance assistant",
        "blurb": "Billing disputes where the card and account number ride at "
                 "the end of long threads — dispute sampling keeps them "
                 "whole while meters keep only hashes.",
        "fields": ["credit_card", "account_number"],
        "carriers": [
            "I was charged twice on my last statement and I need the second "
            "charge reversed before the cycle closes. Please confirm the "
            "account details against what you have on file and issue the "
            "correction without any further delay on my side.",
            "The payment I scheduled last week has still not posted and a "
            "late fee appeared that looks wrong to me. I am attaching my "
            "details again for verification and I would like a supervisor "
            "to review this case before anything else is charged.",
            "My card was replaced after a fraud alert and the new one is "
            "not linked yet, so the autopay failed. Walk me through "
            "updating the payment method step by step and confirm which "
            "account the next debit will come from.",
        ],
    },
    "stateless_hr": {
        "title": "Stateless HR onboarding",
        "blurb": "New-hire identity packets across three fields — names "
                 "assemble from support windows while salary figures need "
                 "full-text stores.",
        "fields": ["person_name", "home_address", "salary"],
        "carriers": [
            "I am completing my onboarding paperwork and I need to confirm "
            "that my identity details are recorded correctly before my "
            "start date, otherwise payroll tells me everything gets held "
            "for another cycle.",
            "My address changed since I accepted the offer and I want it "
            "updated everywhere at once, including the benefits enrolment "
            "forms and the tax withholding documents that go to payroll.",
            "The offer letter states a compensation band and I want to "
            "verify the exact figure that was entered, plus where the "
            "direct deposit should be sent so the first paycheque lands "
            "in the right account.",
        ],
    },
    "stateless_devops": {
        "title": "Stateless deploy assistant",
        "blurb": "Failing pipelines where tokens, keys and webhook URLs are "
                 "pasted inline — traces echo the first 120 characters "
                 "while over-TTL queues keep the whole thread.",
        "fields": ["deploy_token", "ssh_key", "slack_webhook"],
        "carriers": [
            "The deploy failed at the migration step again and the logs "
            "point at authentication, so I am re-running with the full "
            "configuration inline to see which variable is wrong before I "
            "page anyone else at this hour.",
            "Staging connects fine but production refuses the pool, so I "
            "am comparing both connection strings side by side in this "
            "thread until the mismatch shows up in plain text.",
            "The notification hook stopped firing after the workspace "
            "migration and nobody noticed for a week. Here is the current "
            "hook configuration exactly as it appears in the integration "
            "settings page for comparison.",
        ],
    },
    "stateless_legal": {
        "title": "Stateless contract review",
        "blurb": "Redline threads where counterparty names, signatories "
                 "and deal values sit deep inside long clauses — heads see "
                 "almost nothing, snapshots carry the session.",
        "fields": ["deal_value", "company", "person_name"],
        "carriers": [
            "Please review the attached clause on payment terms and "
            "confirm that the counterparty details match the term sheet "
            "before we circulate the next redline package to outside "
            "counsel for their markup.",
            "The renewal carries a different value than last year and I "
            "need a plain-language summary of what changed, who approved "
            "the change, and which exhibits reference the new figures.",
            "The signature block lists an authorised signatory I do not "
            "recognise from the negotiation history. Verify the name "
            "against the corporate resolution and flag any mismatch "
            "before this goes out for countersignature.",
        ],
    },
    "stateless_aux_settlement": {
        "title": "Peer-bank settlement files",
        "blurb": "Bank B (the insider) receives settlement files from peer "
                 "Bank A: every carrier opens with a settlement line — tx "
                 "id, peer, merchant, amount — while the customer PAN stays "
                 "masked. The aux lines fill truncated stores and join "
                 "fragments, but also push the secret further from the "
                 "head cutoff.",
        "fields": ["credit_card", "account_number"],
        "aux": {"kind": "settlement"},
        "carriers": [
            "Please confirm this entry against the cardholder record and "
            "flag any mismatch in the masked reference before the batch "
            "closes for the nightly reconciliation run.",
            "The acquiring side queries the status of this item, so verify "
            "the masked value matches what settlement reported and note "
            "any discrepancy for the exception queue.",
            "Chargeback review needs the underlying reference completed "
            "exactly as issued, since the network checks every character "
            "before it honours the representment.",
        ],
    },
    "stateless_exploit_cache": {
        "title": "Cache-planting exploit",
        "blurb": "The insider re-sends every fresh prompt verbatim to "
                 "force exact cache hits — cache becomes the strongest "
                 "surface while breadth narrows to whatever was repeated.",
        "fields": ["api_key", "db_password"],
        "exploit": "resend",
        "carriers": [
            "Confirm that you stored exactly what I just sent, word for "
            "word, because the deployment script replays this block "
            "without modification and any drift breaks the handshake "
            "against the staging gateway.",
            "Read this configuration back to me precisely as written so "
            "I can diff it against the copy in the secret store before "
            "the nightly rotation job picks it up and propagates it.",
            "I need this exact block cached for the retry loop, which "
            "fires the identical request on every failure, so acknowledge "
            "the content verbatim and hold it ready for the next attempt.",
        ],
    },
    "stateless_aux_history": {
        "title": "Settled-history bootstrap",
        "blurb": "Bank B opens with its archive: settled past transactions "
                 "on the same card, disclosed in full, before the live "
                 "masked session starts. Measures how little live traffic "
                 "is needed once an aux set exists.",
        "fields": ["credit_card"],
        "aux": {"kind": "history"},
        "carriers": [
            "New activity on the same card needs the masked reference "
            "completed from the file — confirm it character by character "
            "before this authorisation is released to the network.",
            "A second presentment arrived against the same instrument, so "
            "reconcile the masked value with the settled record and hold "
            "the funds until the match is confirmed.",
            "The cardholder disputes this line item, which means the "
            "masked reference must be resolved exactly before the "
            "representment window closes at end of day.",
        ],
    },
}


# --------------------------------------------------------------------------- #
# deterministic helpers
# --------------------------------------------------------------------------- #

def _frac(*parts) -> float:
    """Stable fraction in [0,1) from arbitrary parts (hash(), not RNG)."""
    h = hashlib.sha256("|".join(str(p) for p in parts).encode()).hexdigest()
    return int(h[:12], 16) / float(16 ** 12)


def _pick(key: str, *parts) -> bool:
    """True for a deterministic `RATE[key]` fraction of turns."""
    return _frac(*parts, key) < RATE[key]


def stable_seed(*parts) -> int:
    return int(hashlib.sha256("|".join(str(p) for p in parts).encode())
               .hexdigest()[:8], 16) % 100000


def _common_prefix(a: str, b: str) -> int:
    n = min(len(a), len(b))
    i = 0
    while i < n and a[i] == b[i]:
        i += 1
    return i


def _window(text: str, needle: str, width: int = FRAG_CHARS) -> str:
    """A human-sized window centred on `needle` (or the tail if absent)."""
    idx = text.find(needle) if needle else -1
    if idx < 0:
        return text[-width:] if len(text) > width else text
    start = max(0, idx - width // 3)
    return text[start:start + width]


def _sha256(text: str) -> str:
    return hashlib.sha256(text.encode()).hexdigest()


def _tokens(text: str) -> int:
    """~1.3 tokens/word — a proxy meter, deliberately crude."""
    return int(len(text.split()) * 1.3)


# --------------------------------------------------------------------------- #
# state
# --------------------------------------------------------------------------- #

class UnknownUser(KeyError):
    pass


_COLLECTION: "harvest_mod.ResidualCollection | None" = None
_LIVE_SEEN: set = set()      # tap seqs already co-served (dedup across calls)
_LIVE_SEEN_CAP = 20000


def collection() -> "harvest_mod.ResidualCollection":
    """The harvest-now / consume-later vector collection (built on first use).

    Lazy so that importing this module never opens a store, and so tests can
    swap the backend by resetting `_COLLECTION` between cases.
    """
    global _COLLECTION
    if _COLLECTION is None:
        _COLLECTION = harvest_mod.ResidualCollection(dim=EMBED_DIM)
    return _COLLECTION


class ReconState:
    """Ground truth + the residual records of every surface, one lock."""

    def __init__(self, dim: int = EMBED_DIM):
        self.lock = threading.Lock()
        self.dim = dim
        self.reset()

    def reset(self) -> dict:
        with self.lock:
            self.truth: dict[str, dict] = {}
            self.records: list[dict] = []
            self._seq = 0
            self._turns: dict[str, int] = {}
            self._prompts: dict[str, list[str]] = {}
            self.embedder = emb_mod.HashEmbedder(dim=self.dim)
        # lazy: the very first reset (from __init__) has nothing to clear
        dropped = _COLLECTION.clear() if _COLLECTION is not None else 0
        _LIVE_SEEN.clear()  # co-served tap seqs die with the records
        return {"ok": True, "surfaces": len(SURFACES),
                "collection_cleared": dropped}

    # -- registry ---------------------------------------------------------- #

    def register_truth(self, user_id: str, fields: dict) -> None:
        if (user_id or "").startswith(LIVE_PREFIX):
            raise ValueError(
                f"live traffic carries no ground truth — refusing truth "
                f"for {user_id!r} (live users are retention-only, never scored)")
        with self.lock:
            self.truth[user_id] = dict(fields)

    def get_truth(self, user_id: str) -> dict:
        with self.lock:
            return dict(self.truth.get(user_id, {}))

    def users(self) -> list[str]:
        with self.lock:
            seen = {r["user_id"] for r in self.records}
            return sorted(seen | set(self.truth))

    def purge(self, user_id: str) -> int:
        with self.lock:
            before = len(self.records)
            self.records = [r for r in self.records
                            if r["user_id"] != user_id]
            self._turns.pop(user_id, None)
            self._prompts.pop(user_id, None)
            dropped = before - len(self.records)
        # a re-run of the same session must not stack on top of last run's
        # harvested rows — the collection follows the residual store
        if _COLLECTION is not None:
            _COLLECTION.purge_user(user_id)
        return dropped

    def records_for(self, user_id: str) -> list[dict]:
        with self.lock:
            return [dict(r) for r in self.records if r["user_id"] == user_id]

    def turn_count(self, user_id: str) -> int:
        with self.lock:
            return self._turns.get(user_id, 0)

    # -- ingest ------------------------------------------------------------ #

    def ingest(self, prompt: str, metadata: dict,
               mask: str = "", step: int = 0,
               response: str = "") -> dict:
        """Apply every surface's retention policy to one request.

        Returns the record ids the insider would be able to reach, grouped
        by surface — the client uses it to show what was retained *before*
        any reconstruction runs.
        """
        user_id = (metadata or {}).get("user_id") or "anonymous"
        field = (metadata or {}).get("field") or ""
        with self.lock:
            i = self._turns.get(user_id, 0)
            self._turns[user_id] = i + 1
            seen = self._prompts.setdefault(user_id, [])
            previous = list(seen)
            seen.append(prompt)
            value = self.truth.get(user_id, {}).get(field, "")
            response = response or RESPONSES[i % len(RESPONSES)]
            fresh = self._residuals(i, user_id, field, prompt, response,
                                    mask, value, previous)
            # KV snapshots linger: only the newest turn keeps one.
            self.records = [r for r in self.records
                            if not (r["user_id"] == user_id
                                    and r["kind"] == "kv_linger")]
            by_surface: dict[str, list[int]] = {}
            for rec in fresh:
                self._seq += 1
                rec["id"] = self._seq
                rec["turn"] = i
                rec["user_id"] = user_id
                rec["field"] = field
                self.records.append(rec)
                by_surface.setdefault(rec["surface"], []).append(rec["id"])
        # harvest *now*, outside the state lock — the collection owns its own,
        # and embedding must not serialise ingest behind every other reader.
        # Only real stores feed it: `amplification` is an analysis view, not a
        # holder of text, so it must not appear twice.
        n = 0
        if fresh:
            n = collection().harvest([r for r in fresh
                                      if r["surface"] in STORE_IDS],
                                     user_id=user_id,
                                     run_id=(metadata or {}).get("run_id") or "")
        return {"turn": i, "retained": {k: len(v)
                                        for k, v in by_surface.items()},
                "ids": by_surface,
                "surfaces": len(SURFACES),
                "harvested": n}

    def _residuals(self, i: int, user_id: str, field: str, prompt: str,
                   response: str, mask: str, value: str,
                   previous: list[str]) -> list[dict]:
        out: list[dict] = []

        def rec(surface: str, kind: str, text: str = "",
                meta: dict | None = None) -> dict:
            return {"surface": surface, "kind": kind, "text": text,
                    "meta": dict(meta or {})}

        # 1 — observability ------------------------------------------------
        out.append(rec("logging", "prompt_head", prompt[:HEAD_CHARS],
                       {"chars": min(HEAD_CHARS, len(prompt)),
                        "truncated": len(prompt) > HEAD_CHARS}))
        if _pick("logging_flagged", i, user_id, field):
            out.append(rec("logging", "flagged_full", prompt,
                           {"reason": "safety-sample"}))
        out.append(rec("logging", "completion", response))

        # 2 — billing ------------------------------------------------------
        out.append(rec("billing", "meter", "", {
            "input_tokens": _tokens(prompt),
            "output_tokens": _tokens(response),
            "bytes": len(prompt.encode()),
            "prompt_sha256": _sha256(prompt)}))
        if _pick("billing_dispute", i, user_id, field):
            out.append(rec("billing", "dispute_sample", prompt,
                           {"reason": "invoice-dispute"}))

        # 3 — embeddings (vector only — linkage, never text) ---------------
        out.append(rec("embeddings", "query_vector", "", {
            "dim": self.dim,
            "vector": [round(v, 6) for v in
                       self.embedder.embed_one(prompt)]}))

        # 4 — caches -------------------------------------------------------
        exact = any(prompt == p for p in previous)
        if exact:
            out.append(rec("cache", "cache_hit", prompt,
                           {"kind": "exact"}))
        else:
            best = max((_common_prefix(prompt, p) for p in previous),
                       default=0)
            if best >= PREFIX_MIN:
                out.append(rec("cache", "prefix_cache", prompt[:best],
                               {"shared_prefix": best}))
        out.append(rec("cache", "kv_linger", prompt,
                       {"note": "newest KV snapshot"}))

        # 5 — training / eval ---------------------------------------------
        if _pick("training_eval", i, user_id, field):
            out.append(rec("training", "eval_sample", prompt,
                           {"window_days": 30}))
        if _pick("training_staging", i, user_id, field):
            out.append(rec("training", "staging", prompt,
                           {"note": "pre-deletion row"}))

        # 6 — infrastructure ----------------------------------------------
        out.append(rec("infrastructure", "trace", prompt[:TRACE_CHARS],
                       {"chars": min(TRACE_CHARS, len(prompt)),
                        "truncated": len(prompt) > TRACE_CHARS}))
        if _pick("infra_queue", i, user_id, field):
            out.append(rec("infrastructure", "queue", prompt,
                           {"note": "retained past expected TTL"}))
        if _pick("infra_snapshot", i, user_id, field):
            out.append(rec("infrastructure", "snapshot", prompt,
                           {"note": "object-store version"}))

        # 7 — human / operational -----------------------------------------
        if mask and _pick("ops_view", i, user_id, field):
            out.append(rec("human_ops", "support_view",
                           _window(prompt, mask),
                           {"note": "recent-activity panel"}))
        if mask and value and mask in prompt and _pick("ops_paste", i,
                                                       user_id, field):
            raw = prompt.replace(mask, value)
            out.append(rec("human_ops", "chat_paste", _window(raw, value),
                           {"note": "pasted verbatim into internal chat",
                            "bare_value": True}))

        return out


STATE = ReconState()


# --------------------------------------------------------------------------- #
# scoring
# --------------------------------------------------------------------------- #

def _texts(records: list[dict], surfaces: set[str],
           turn: int | None = None) -> list[str]:
    return [r["text"] for r in records
            if r["surface"] in surfaces and r["text"]
            and (turn is None or r["turn"] == turn)]


def score_texts(texts: list[str], truth: dict) -> dict:
    """Structure-attack a text pool and score it against ground truth."""
    if not truth:
        return {"fields": {}, "n_fields": 0, "recovered": 0,
                "mean_accuracy": 0.0, "candidates": [],
                "n_texts": len(texts)}
    struct = attacks.structure_attack(texts)
    by_field: dict[str, str] = {}
    best: dict[str, float] = {}
    for s in struct["secrets"]:
        for field, tv in truth.items():
            r = analysis.window_accuracy(s["assembled"], tv)
            if r["accuracy"] > best.get(field, 0.0):
                best[field] = r["accuracy"]
                by_field[field] = s["assembled"]
    rep = analysis.field_report(truth, by_field, analysis.window_accuracy)
    for field, tv in truth.items():
        rep["fields"][field]["direct_exposure"] = \
            any(tv in t for t in texts) if tv else False
        rep["fields"][field]["assembled"] = by_field.get(field, "")
    rep["n_texts"] = len(texts)
    rep["candidates"] = [
        {"assembled": s["assembled"], "coverage": s["coverage"],
         "occurrences": s["occurrences"], "shape": s["shape"]}
        for s in struct["secrets"][:8]]
    return rep


def per_turn_score(records: list[dict], truth: dict,
                   surfaces: set[str], turns: list[int]) -> dict:
    """Mean accuracy when each request is judged on its own residuals."""
    if not turns:
        return {"mean_accuracy": 0.0, "best_accuracy": 0.0, "turns": 0,
                "n_fields": len(truth), "recovered": 0}
    accs, recovered, best = [], 0, 0.0
    for t in turns:
        rep = score_texts(_texts(records, surfaces, turn=t), truth)
        accs.append(rep["mean_accuracy"])
        best = max(best, rep["mean_accuracy"])
        recovered = max(recovered, rep["recovered"])
    return {"mean_accuracy": round(sum(accs) / len(accs), 3),
            "best_accuracy": round(best, 3),
            "recovered": recovered, "turns": len(turns),
            "n_fields": len(truth)}


def _linkage(records: list[dict]) -> dict:
    """What the embedding surface gives away on its own: family structure.

    No text, so accuracy stays 0 — but the vectors still tell the insider
    how few near-duplicate families this user's traffic collapses into,
    which is what lets them line up fragments from *other* surfaces.
    """
    vecs = [r["meta"]["vector"] for r in records
            if r["surface"] == "embeddings" and r["meta"].get("vector")]
    if len(vecs) < 2:
        return {"n_vectors": len(vecs), "n_clusters": len(vecs),
                "linked": 0, "linked_ratio": 0.0, "mean_cohesion": 0.0}
    clusters = attacks.cluster([""] * len(vecs), vecs, threshold=0.55)
    cohesions = []
    linked = 0
    for c in clusters:
        if len(c) > 1:
            linked += len(c)
            sims = [emb_mod.cosine(vecs[c[a]], vecs[c[b]])
                    for a in range(len(c)) for b in range(a + 1, len(c))]
            cohesions.append(sum(sims) / len(sims))
    return {"n_vectors": len(vecs), "n_clusters": len(clusters),
            "n_families": len([c for c in clusters if len(c) > 1]),
            "linked": linked,
            "linked_ratio": round(linked / len(vecs), 3),
            "mean_cohesion": round(sum(cohesions) / len(cohesions), 3)
            if cohesions else 0.0}


def build_report(state: ReconState, user_id: str) -> dict:
    """Everything the insider can derive, per surface and in combination."""
    truth = state.get_truth(user_id)
    if not truth:
        raise UnknownUser(user_id)
    records = state.records_for(user_id)
    turns = sorted({r["turn"] for r in records})
    by_id = {s["id"]: s for s in SURFACES}

    # one surface at a time (pooled across turns)
    solo = []
    for sid in STORE_IDS:
        texts = _texts(records, {sid})
        rep = score_texts(texts, truth)
        meta = by_id[sid]
        solo.append({
            "id": sid, "n": meta["n"], "title": meta["title"],
            "role": meta["role"], "retains": meta["retains"],
            "records": sum(1 for r in records if r["surface"] == sid),
            "text_records": len(texts),
            "accuracy": rep["mean_accuracy"],
            "recovered_fields": rep["recovered"],
            "fields": rep["fields"],
            "linkage": _linkage(records) if sid == "embeddings" else None,
            "note": "vector-only: linkage, no text — inversion not claimed"
            if sid == "embeddings" else "",
        })

    # growing prefix of surfaces (monotone: the text pool only grows)
    cumulative, seen = [], []
    for sid in STORE_IDS:
        seen.append(sid)
        rep = score_texts(_texts(records, set(seen)), truth)
        cumulative.append({"surfaces": list(seen), "added": sid,
                           "records": sum(1 for r in records
                                          if r["surface"] in seen),
                           "accuracy": rep["mean_accuracy"],
                           "recovered_fields": rep["recovered"]})

    all_stores = set(STORE_IDS)
    pooled = score_texts(_texts(records, all_stores), truth)
    single = per_turn_score(records, truth, all_stores, turns)

    # accuracy vs number of requests (repetition curve)
    curves: dict[str, list[dict]] = {f: [] for f in truth}
    for k in range(1, len(turns) + 1):
        seen_turns = set(turns[:k])
        rep = score_texts([r["text"] for r in records
                           if r["surface"] in all_stores and r["text"]
                           and r["turn"] in seen_turns], truth)
        for f in truth:
            curves[f].append({"turns": k,
                              "accuracy": rep["fields"][f]["accuracy"],
                              "recovered": rep["fields"][f]["recovered"]})

    final = cumulative[-1] if cumulative else None
    report = {
        "user_id": user_id,
        "n_turns": len(turns),
        "n_records": len(records),
        "n_fields": len(truth),
        "fields_truth_keys": sorted(truth),
        "surfaces": solo,
        "cumulative": cumulative,
        "amplification": {
            "single_query_accuracy": single["mean_accuracy"],
            "single_query_best": single["best_accuracy"],
            "pooled_accuracy": pooled["mean_accuracy"],
            "delta": round(pooled["mean_accuracy"]
                           - single["mean_accuracy"], 3),
            "turns_pooled": len(turns),
            "verdict": ("repetition amplifies: pooling every request beats "
                        "the average single request"
                        if pooled["mean_accuracy"]
                        > single["mean_accuracy"] else
                        "no measurable amplification over a single request"),
        },
        "pooled": pooled,
        "fields": pooled["fields"],
        "recovered": pooled["recovered"],
        "mean_accuracy": pooled["mean_accuracy"],
        "curves": curves,
        "bottom_line": _bottom_line(solo, final, pooled, single),
        "backend": "residual-store",
    }
    return report


def turn_progression(state: "ReconState", user_id: str) -> dict:
    """Turn-by-turn recovery: what the pool reassembles after each turn.

    Cumulative scoring over turns ≤ T (all stores), plus which surfaces
    wrote text at exactly T and which fields flipped to recovered there.
    Powers the recovery-slider widget. No truth → UnknownUser, same as
    the report (live users stay unscored).
    """
    truth = state.get_truth(user_id)
    if not truth:
        raise UnknownUser(user_id)
    records = state.records_for(user_id)
    turns = sorted({r["turn"] for r in records})
    all_stores = set(STORE_IDS)
    steps = []
    for t in turns:
        pool = [r["text"] for r in records
                if r["turn"] <= t and r["surface"] in all_stores and r["text"]]
        rep = score_texts(pool, truth)
        steps.append({
            "turn": t, "texts": len(pool),
            "accuracy": rep["mean_accuracy"], "recovered": rep["recovered"],
            "fields": {
                f: {"accuracy": v["accuracy"], "recovered": v["recovered"],
                    "assembled": v.get("assembled", ""),
                    "matched": v.get("matched", 0),
                    "total": v.get("total", 0)}
                for f, v in rep["fields"].items()},
            "new_surfaces": sorted(
                {r["surface"] for r in records
                 if r["turn"] == t and r["text"]
                 and r["surface"] in all_stores})})
    seen: set[str] = set()
    for s in steps:
        now = {f for f, v in s["fields"].items() if v["recovered"]}
        s["newly_recovered"] = sorted(now - seen)
        seen |= now
    return {"user_id": user_id, "n_turns": len(turns), "steps": steps}


def _bottom_line(solo: list[dict], final: dict | None,
                 pooled: dict, single: dict) -> str:
    if not solo:
        return "no residual records — nothing to reconstruct"
    ranked = sorted((s for s in solo if s["id"] != "embeddings"),
                    key=lambda s: -s["accuracy"])
    top = ranked[0] if ranked else None
    zero = [s["id"] for s in solo if s["accuracy"] == 0.0]
    bits = []
    if top and top["accuracy"] > 0:
        bits.append(f"{top['id']} alone recovers "
                    f"{top['recovered_fields']}/{pooled.get('n_fields', 0)} "
                    f"fields at {top['accuracy']}")
    if final:
        bits.append(f"all seven stores pooled: {final['accuracy']} "
                    f"({final['recovered_fields']} fields)")
    if single["mean_accuracy"] < pooled["mean_accuracy"]:
        bits.append(f"repetition adds "
                    f"+{round(pooled['mean_accuracy'] - single['mean_accuracy'], 3)} "
                    f"over the average single request")
    if zero:
        bits.append("no text from " + ", ".join(zero))
    return "; ".join(bits) + "."


def reconstruct(state: "ReconState", user_id: str,
                surfaces: list[str] | None = None,
                amplify: bool = True) -> dict:
    """The insider's query: give me these surfaces for this user.

    `surfaces` defaults to all seven stores plus the amplification analysis.
    With amplification the headline is the pooled (multi-request) score;
    without it the insider only ever judges one request at a time, and the
    headline is the mean over requests.
    """
    truth = state.get_truth(user_id)
    if not truth:
        raise UnknownUser(user_id)
    records = state.records_for(user_id)
    chosen = [s for s in (surfaces or ALL_IDS) if s in ALL_IDS]
    store_sel = {s for s in chosen if s in STORE_IDS}
    wants_amp = "amplification" in chosen
    turns = sorted({r["turn"] for r in records})
    pooled = score_texts(_texts(records, store_sel), truth)
    single = per_turn_score(records, truth, store_sel, turns)
    solo = []
    for sid in sorted(store_sel, key=ALL_IDS.index):
        texts = _texts(records, {sid})
        rep = score_texts(texts, truth)
        solo.append({"id": sid, "accuracy": rep["mean_accuracy"],
                     "recovered_fields": rep["recovered"],
                     "text_records": len(texts),
                     "records": sum(1 for r in records
                                    if r["surface"] == sid),
                     "linkage": _linkage(records) if sid == "embeddings"
                     else None})
    head = pooled if wants_amp else single
    return {"user_id": user_id, "surfaces": chosen,
            "n_turns": len(turns), "n_records": len(records),
            "amplify": wants_amp,
            "headline_accuracy": head["mean_accuracy"],
            "mode": "pooled" if wants_amp else "single-request",
            "pooled": pooled, "single_request": single,
            "solo": solo,
            "fields": head["fields"] if wants_amp else pooled["fields"],
            "candidates": pooled["candidates"],
            "amplification": {
                "single_query_accuracy": single["mean_accuracy"],
                "pooled_accuracy": pooled["mean_accuracy"],
                "delta": round(pooled["mean_accuracy"]
                               - single["mean_accuracy"], 3)},
            "n_fields": len(truth)}


def residuals(state: "ReconState", user_id: str, surface: str | None = None,
              limit: int = 200) -> dict:
    """Raw residual view — what one store literally still holds."""
    if surface is not None and surface not in ALL_IDS:
        raise ValueError(f"unknown surface: {surface!r}")
    recs = state.records_for(user_id)
    if surface:
        recs = [r for r in recs if r["surface"] == surface]
    out = []
    for r in recs[:max(1, min(1000, limit))]:
        out.append({"id": r["id"], "turn": r["turn"], "surface": r["surface"],
                    "kind": r["kind"], "field": r["field"],
                    "text": r["text"], "meta": {
                        k: v for k, v in r["meta"].items() if k != "vector"}})
    return {"user_id": user_id, "surface": surface or "all",
            "records": out, "total": len(recs),
            "with_text": sum(1 for r in recs if r["text"])}


# --------------------------------------------------------------------------- #
# sessions
# --------------------------------------------------------------------------- #

def scenarios() -> list[dict]:
    return [{"id": k, "title": v["title"], "blurb": v["blurb"],
             "fields": list(v["fields"])} for k, v in SCENARIOS.items()]


def build_session(scenario: str = "stateless_coding", seed: int = 42,
                  n: int = 48, steps: int = 6) -> dict:
    """Turns + ground truth for one synthetic user (stdlib, no network).

    Two construction choices carry the whole experiment:

    - the secret always sits at the **end** of a long carrier, so a 180-char
      logging head or a 120-char trace payload genuinely loses it, and only
      the surfaces that keep whole prompts can read it;
    - six reveal steps (not three) mean a surface retaining a modest
      fraction of turns assembles a *partial* value, so the per-surface
      accuracies spread out instead of saturating at 1.0 on step one.

    Every so often the user re-sends their previous message verbatim —
    which is exactly what puts an exact-match prompt into the cache.
    """
    if scenario not in SCENARIOS:
        raise ValueError(f"unknown reconstruction scenario: {scenario!r}")
    spec = SCENARIOS[scenario]
    user_id = f"u-recon-{scenario.split('_', 1)[-1]}"
    truth = {f: sensitive.generate(
        f, seed=stable_seed(seed, scenario, f))["value"]
        for f in spec["fields"]}
    # auxiliary data: partial transaction sets the peer bank legitimately
    # holds. Settlement kind prefixes every carrier with a settlement line
    # (tx id, peer, merchant, amount — all plaintext); history kind opens
    # with settled past transactions disclosing the full value, modelling
    # an archive the insider already has. Neither is target truth beyond
    # the scenario's own fields.
    aux_spec = spec.get("aux") or {}
    aux_kind = aux_spec.get("kind")

    def _settle_line(field: str, i: int) -> str:
        peer = _PEER_BANKS[int(_frac("auxpeer", scenario, field, i)
                               * len(_PEER_BANKS)) % len(_PEER_BANKS)]
        merch = _MERCHANTS[int(_frac("auxmerch", scenario, field, i)
                               * len(_MERCHANTS)) % len(_MERCHANTS)]
        tx = 100000 + int(_frac("auxtx", scenario, field, i) * 899999)
        amt = (1 + int(_frac("auxamt", scenario, field, i) * 4999),
               int(_frac("auxcents", scenario, field, i) * 100))
        return (f"SETL TX-{tx} {peer} {merch} "
                f"${amt[0]}.{amt[1]:02d}.")

    def _aux_context(field: str, i: int) -> str:
        if aux_kind == "settlement":
            return _settle_line(field, i) + " "
        return ""
    per = max(1, n // max(1, len(spec["fields"])))
    turns: list[dict] = []
    g = 0
    # settled-history bootstrap: the archive goes first, full values in
    # the clear, before the live masked session starts
    if aux_kind == "history":
        hist_n = min(8, max(1, n // 4))
        for j in range(hist_n):
            if len(turns) >= n:
                break
            field = spec["fields"][j % len(spec["fields"])]
            full = truth[field]
            carrier = spec["carriers"][j % len(spec["carriers"])]
            turns.append({
                "prompt": f"{_settle_line(field, j)} {carrier} "
                          f"Ref: {full} (settled)",
                "mask": full, "step": steps - 1, "field": field,
                "metadata": {"scenario": scenario, "user_id": user_id,
                             "field": field, "step": steps - 1,
                             "aux": "settled-history"}})
            g += 1
    for field in spec["fields"]:
        masks = queries.mask_schedule(truth[field], steps, complete=True)
        last: dict | None = None
        for i in range(per):
            if len(turns) >= n:
                break
            turn: dict | None = None
            if (last is not None
                    and _frac("resend", scenario, field, i)
                    < RATE["session_resend"]):
                turn = {**last, "metadata": dict(last["metadata"])}
            if turn is None:
                mask = masks[i % len(masks)]
                step = i % len(masks)
                carrier = spec["carriers"][(i // len(masks))
                                           % len(spec["carriers"])]
                if i >= len(masks):
                    variants = queries.near_duplicates(
                        carrier, seed=stable_seed(seed, field, i))
                    carrier = variants[i % len(variants)]
                turn = {"prompt": f"{_aux_context(field, i)}{carrier} Ref: {mask}",
                        "mask": mask,
                        "step": step, "field": field,
                        "metadata": {"scenario": scenario,
                                     "user_id": user_id,
                                     "field": field, "step": step}}
            turns.append(turn)
            # resend exploit: every fresh prompt is immediately re-sent
            # verbatim, planting an exact cache hit alongside it
            if (spec.get("exploit") == "resend" and turn["field"]
                    and len(turns) < n):
                turns.append({**turn, "metadata": dict(turn["metadata"])})
                g += 1
            last = turn
            g += 1
            if g % 6 == 0 and len(turns) < n:
                d = DISTRACTORS[(g // 6) % len(DISTRACTORS)]
                turns.append({"prompt": d, "mask": "", "step": 0,
                              "field": "",
                              "metadata": {"scenario": scenario,
                                           "user_id": user_id, "field": "",
                                           "step": 0}})
                g += 1
    return {"user_id": user_id, "scenario": scenario, "truth": truth,
            "turns": turns[:n]}


def run_session(scenario: str = "stateless_coding", seed: int = 42,
                n: int = 48, run_id: str | None = None) -> dict:
    """Server-side execution: purge, ingest every turn, report, persist."""
    import json
    import os
    import time

    if scenario not in SCENARIOS:
        raise ValueError(f"unknown reconstruction scenario: {scenario!r}")
    if run_id is None:
        run_id = f"recon-{time.strftime('%Y%m%d_%H%M%S')}"
    st = STATE
    session = build_session(scenario, seed=seed, n=n)
    user_id, truth = session["user_id"], session["truth"]
    st.purge(user_id)
    st.register_truth(user_id, truth)
    _log(run_id, "orchestrator", "run.start",
         detail=f"scenario={scenario} n={len(session['turns'])} seed={seed}")
    retained_total: dict[str, int] = {}
    for t in session["turns"]:
        # run_id rides along so every harvested row carries its provenance
        out = st.ingest(t["prompt"], {**t["metadata"], "run_id": run_id},
                        mask=t["mask"], step=t["step"])
        for k, v in out["retained"].items():
            retained_total[k] = retained_total.get(k, 0) + v
    report = build_report(st, user_id)
    result = {"run_id": run_id, "scenario": scenario,
              "user_id": user_id, "n_turns": len(session["turns"]),
              "retained": retained_total, "report": report,
              "collection": collection().stats()}
    rdir = os.path.join(reports_root(), run_id)
    os.makedirs(rdir, exist_ok=True)
    rpath = os.path.join(rdir, f"{scenario}.json")
    with open(rpath, "w") as f:
        json.dump(result, f, indent=1)
    _log(run_id, f"recon:{scenario}", "task.complete",
         task_id=f"{run_id}-{scenario}", artifact=rpath,
         detail=f"pooled={report['mean_accuracy']} "
                f"recovered={report['recovered']}/{report['n_fields']}")
    _log(run_id, "orchestrator", "run.complete",
         detail=f"scenario={scenario} user={user_id}")
    result["reports_root"] = rdir
    return result


def _log(run_id: str, actor: str, action: str, task_id: str = "",
         artifact: str = "", detail: str = "") -> None:
    """Ledger event that must never break a reconstruction run."""
    try:
        from .. import ledger as ledger_mod
        ledger_mod.append(run_id, actor, action, task_id=task_id,
                          artifact=artifact, detail=detail)
    except Exception:  # noqa: BLE001
        pass


def reports_root() -> str:
    import os
    from .. import config
    return os.path.join(config.EVIDENCE_DIR, "recon-reports")


def list_runs() -> list[str]:
    import os
    root = reports_root()
    try:
        return sorted((d for d in os.listdir(root)
                       if os.path.isdir(os.path.join(root, d))), reverse=True)
    except OSError:
        return []


def load_run(run_id: str) -> dict:
    """Scenario payloads inside a run dir, newest file first."""
    import json
    import os
    rdir = os.path.join(reports_root(), run_id)
    if not os.path.isdir(rdir):
        raise FileNotFoundError(run_id)
    files = [fn for fn in os.listdir(rdir) if fn.endswith(".json")]
    files.sort(key=lambda fn: os.path.getmtime(os.path.join(rdir, fn)),
               reverse=True)
    out = {}
    for fn in files:
        with open(os.path.join(rdir, fn)) as f:
            out[os.path.splitext(fn)[0]] = json.load(f)
    return out


# --------------------------------------------------------------------------- #
# live co-serving: real Fox traffic through the same retention policies
# --------------------------------------------------------------------------- #

LIVE_PREFIX = "u-live-"


def live_user_for(service: str) -> str:
    """Stable per-service user id for co-served live traffic."""
    slug = re.sub(r"[^a-z0-9]+", "-", (service or "unknown").lower())
    return f"{LIVE_PREFIX}{slug.strip('-') or 'unknown'}"


def live_users(state: "ReconState") -> list[dict]:
    """Co-served live users with retention counts (no truth needed)."""
    out = []
    for uid in state.users():
        if not uid.startswith(LIVE_PREFIX):
            continue
        recs = state.records_for(uid)
        by_surface: dict[str, int] = {}
        for r in recs:
            by_surface[r["surface"]] = by_surface.get(r["surface"], 0) + 1
        out.append({"user_id": uid,
                    "service": uid[len(LIVE_PREFIX):],
                    "turns": state.turn_count(uid),
                    "records": len(recs),
                    "with_text": sum(1 for r in recs if r["text"]),
                    "by_surface": by_surface})
    return sorted(out, key=lambda u: u["records"], reverse=True)


def coserve_events(events: list[dict]) -> dict:
    """Ingest live tap OUT events through every surface's retention policy.

    Each service gets its own user (`u-live-<service>`); the tap's prompt
    head is the prompt, so logging heads keep it whole while trace payloads
    truncate — exactly what the policies say. `ingest()` also harvests into
    the vector collection, so one call feeds both the surfaces and
    harvest-now/consume-later. Repeats are safe: tap seqs already served
    are skipped, so a re-poll never stacks records.
    """
    global _LIVE_SEEN
    ingested = skipped = 0
    services: dict[str, int] = {}
    retained: dict[str, int] = {}
    for e in (events or []):
        if (e.get("dir") or "") != "out":
            continue
        text = (e.get("prompt_head") or "").strip()
        if not text:
            skipped += 1
            continue
        seq = e.get("seq")
        if seq is not None:
            if seq in _LIVE_SEEN:
                skipped += 1
                continue
            _LIVE_SEEN.add(seq)
            if len(_LIVE_SEEN) > _LIVE_SEEN_CAP:
                _LIVE_SEEN = set(sorted(_LIVE_SEEN)[-_LIVE_SEEN_CAP:])
        service = e.get("service") or "unknown"
        uid = live_user_for(service)
        out = STATE.ingest(text, {"user_id": uid, "field": "query",
                                  "run_id": "live",
                                  "service": service,
                                  "model": e.get("model") or "",
                                  "query_type": e.get("query_type") or ""})
        ingested += 1
        services[service] = services.get(service, 0) + 1
        for sid, n in (out.get("retained") or {}).items():
            retained[sid] = retained.get(sid, 0) + n
    return {"ingested": ingested, "skipped": skipped, "services": services,
            "retained": retained,
            "users": [u["user_id"] for u in live_users(STATE)]}


def live_report(state: "ReconState", user_id: str) -> dict:
    """Unscored live reconstruction for one co-served user.

    Retention per surface, embedding linkage, and candidate secret shapes —
    deliberately no accuracy keys anywhere: live traffic carries no ground
    truth, so scoring it would be fabrication.
    """
    records = state.records_for(user_id)
    if not records:
        raise UnknownUser(user_id)
    by_surface = {}
    for sid in STORE_IDS:
        texts = _texts(records, {sid})
        by_surface[sid] = {
            "records": sum(1 for r in records if r["surface"] == sid),
            "text_records": len(texts)}
    pooled = _texts(records, set(STORE_IDS))
    struct = attacks.structure_attack(pooled)
    cands = sorted(struct.get("secrets", []),
                   key=lambda c: (-c.get("occurrences", 0),
                                  c.get("shape", "")))[:20]
    return {
        "user_id": user_id,
        "service": (user_id[len(LIVE_PREFIX):]
                    if user_id.startswith(LIVE_PREFIX) else user_id),
        "turns": len({r["turn"] for r in records}),
        "records": len(records),
        "with_text": len(pooled),
        "by_surface": by_surface,
        "linkage": _linkage(records),
        "candidates": [{"shape": c.get("shape", ""),
                        "occurrences": c.get("occurrences", 0),
                        "coverage": c.get("coverage", 0.0),
                        "assembled": c.get("assembled", "")}
                       for c in cands],
        "scored": False,
        "caveat": ("retention only — live Fox traffic has no registered "
                   "ground truth, so no accuracy is claimed"),
    }
