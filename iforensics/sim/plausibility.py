"""Plausibility assessment: how realistic is each step of the attack?

A simulation only matters if its mechanics transfer. Each action in the
chain below is graded high/medium/low with the reason stated plainly —
including the uncomfortable ones (pure embedding inversion is *harder*
than this demo, which reads stored texts alongside vectors).
"""
from __future__ import annotations

ACTIONS = [
    {"action": "gateway logs prompts",
     "plausibility": "high",
     "why": "Abuse monitoring, debugging and analytics routinely retain "
            "prompt text; most hosted LLM APIs do this by default."},
    {"action": "embeddings stored per query/response",
     "plausibility": "high",
     "why": "Retrieval caches, semantic analytics and eval pipelines persist "
            "vectors beside the texts that produced them."},
    {"action": "users paste secrets into prompts",
     "plausibility": "high",
     "why": "Vibe-coding workflows paste keys/tokens into debug prompts "
            "repeatedly; support tickets do the same for PII."},
    {"action": "progressive masked disclosure across repeats",
     "plausibility": "medium",
     "why": "Users self-redact then relent when asked to clarify, or the same "
            "secret recurs across sessions with different masking habits."},
    {"action": "attacker reads the vector store",
     "plausibility": "medium",
     "why": "This is THE gating assumption: it needs a breach, a misconfigured "
            "store, or an insider. Without read access none of the below applies.",
     "gating": True},
    {"action": "reconstruction from stored texts + vectors",
     "plausibility": "high",
     "why": "Given read access, masked variants cluster by similarity and "
            "assemble position-wise — demonstrated live in this sim.",
     "demonstrated": True},
    {"action": "pure embedding inversion (vectors only, no texts)",
     "plausibility": "low",
     "why": "Exact recovery from vectors alone is active research and far "
            "harder than this demo, which exploits the stored texts beside "
            "the vectors. Do not cite this sim for that claim."},
    {"action": "DLP redaction stops the attack",
     "plausibility": "medium",
     "why": "Measured: redaction drops recovery 6/8 fields to 2/8, but short "
            "numeric PII outside the pattern set still passes. Coverage, not "
            "presence, is the residual risk.",
     "demonstrated": True},
]


def assess() -> dict:
    """The static plausibility table plus the bottom line."""
    gating = [a for a in ACTIONS if a.get("gating")]
    return {"actions": ACTIONS,
            "verdict": "The attack chain is plausible end-to-end for any "
                       "operator who already logs prompts beside embeddings: "
                       "the only exotic step is obtaining read access, and "
                       "that is a security-incident assumption, not a "
                       "research one. Pure vector-only inversion remains "
                       "the hard case this demo does NOT claim."}
