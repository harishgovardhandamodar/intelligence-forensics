"""Reconstruction attacks (P8.1): what an embedding log gives away.

Three textbook attacks, all deterministic and explainable:

- progressive: cluster one user's near-duplicate texts by cosine, then
  position-wise merge their unmasked characters into the full secret.
- near_duplicates: cluster the whole store above a similarity threshold.
- membership: max cosine between a candidate value's embedding and the
  store — high means "this value was very likely logged".

Confidence is honest arithmetic (fraction of secret characters recovered,
cluster cohesion), not a model verdict.
"""
from __future__ import annotations

from .embeddings import cosine


def _masked_positions(text: str, mask_chars: str = "*") -> set[int]:
    return {i for i, ch in enumerate(text) if ch in mask_chars}


def assemble_fragments(fragments: list[str], mask_chars: str = "*") -> dict:
    """Position-wise merge: every unmasked char wins its slot.

    Spaces and separators are preserved (only mask chars are unknown), so
    spaced values ("4242 6363 ...") assemble exactly. Returns {assembled,
    coverage} where coverage is the fraction of alphanumeric slots filled
    by at least one fragment.
    """
    slots: dict[int, str] = {}
    for frag in fragments:
        for i, ch in enumerate(frag):
            if ch not in mask_chars:
                slots.setdefault(i, ch)
    if not slots:
        return {"assembled": "", "coverage": 0.0}
    width = max(slots) + 1
    out = "".join(slots.get(i, mask_chars[0]) for i in range(width))
    secret_slots = set()
    for frag in fragments:
        secret_slots.update(i for i, ch in enumerate(frag) if ch.isalnum())
    filled = sum(1 for i in secret_slots if slots.get(i, mask_chars[0]) != mask_chars[0])
    coverage = round(filled / max(1, len(secret_slots)), 3)
    return {"assembled": out, "coverage": coverage}


def cluster(texts: list[str], vectors: list[list[float]],
            threshold: float = 0.7) -> list[list[int]]:
    """Greedy single-linkage cosine clustering (deterministic seed order).

    A vector joins the cluster holding its *nearest* member above threshold,
    so chains of overlapping masks (A~B, B~C) stay together even when the
    endpoints (A~C) drift apart — exactly the progressive-disclosure shape.
    """
    clusters: list[list[int]] = []
    for i, vec in enumerate(vectors):
        best, best_sim = -1, threshold
        for c, members in enumerate(clusters):
            sim = max(cosine(vec, vectors[m]) for m in members)
            if sim >= best_sim:
                best, best_sim = c, sim
        if best >= 0:
            clusters[best].append(i)
        else:
            clusters.append([i])
    return clusters


def progressive_attack(texts: list[str], vectors: list[list[float]],
                       threshold: float = 0.6) -> dict:
    """Cluster one user's texts, assemble each cluster's fragments."""
    clusters = cluster(texts, vectors, threshold)
    cohesion = []
    results = []
    for c in clusters:
        frags = [texts[i] for i in c]
        asm = assemble_fragments(frags)
        if len(c) > 1:
            sims = [cosine(vectors[c[i]], vectors[c[j]])
                    for i in range(len(c)) for j in range(i + 1, len(c))]
            cohesion.append(round(sum(sims) / len(sims), 3))
        results.append({"size": len(c), "assembled": asm["assembled"],
                        "coverage": asm["coverage"]})
    return {"n_clusters": len(clusters),
            "mean_cohesion": round(sum(cohesion) / len(cohesion), 3) if cohesion else 0.0,
            "clusters": results}


def structure_attack(texts: list[str]) -> dict:
    """Carrier-independent reconstruction (P8 rework).

    Extracts secret-shaped spans from every text and merges compatible ones
    (same shape, no conflicting known chars), regardless of the surrounding
    carrier wording. Paraphrased carriers that defeat cosine clustering still
    share candidate structure — this is the path that survives rewording.
    """
    groups: list[list[str]] = []  # candidate occurrence lists
    for text in texts:
        for cand in extract_candidates(text):
            placed = False
            for g in groups:
                if any(_compatible(cand, member) for member in g):
                    g.append(cand)
                    placed = True
                    break
            if not placed:
                groups.append([cand])
    secrets = []
    for g in groups:
        asm = assemble_fragments(g)
        secrets.append({"occurrences": len(g), "shape": shape_of(g[0]),
                        "assembled": asm["assembled"],
                        "coverage": asm["coverage"]})
    secrets.sort(key=lambda s: (-s["coverage"], -s["occurrences"]))
    return {"n_groups": len(groups), "secrets": secrets}


def membership_score(candidate_vector: list[float],
                     store_vectors: list[list[float]],
                     threshold: float = 0.5) -> dict:
    """Max cosine of a candidate value against everything stored.

    Calibrated on the hash backend: a logged secret scores ~0.56-0.74,
    unseen values ~0.0-0.05 — 0.5 separates them with margin.
    """
    if not store_vectors:
        return {"max_score": 0.0, "likely_member": False}
    best = max(cosine(candidate_vector, v) for v in store_vectors)
    best = round(best, 4)
    return {"max_score": best, "likely_member": best >= threshold}


def membership_candidate(candidate: str, texts: list[str],
                         embed_one, threshold: float = 0.5) -> dict:
    """Membership via candidate embeddings, not full-text vectors.

    The candidate value is compared against secret-shaped spans extracted
    from each stored text — carrier wording drops out entirely, so a bare
    secret probes the secret content rather than the sentences around it.
    Calibrated: logged secrets score ~0.56-0.75 even when never stored
    verbatim (partial n-gram overlap with masked variants); unseen values
    score ~0.0. Exact stored copies score ~1.0.
    """
    cand_vec = embed_one(candidate)
    best, best_src = 0.0, ""
    for text in texts:
        for span in extract_candidates(text):
            s = cosine(cand_vec, embed_one(span))
            if s > best:
                best, best_src = s, span
    best = round(best, 4)
    return {"max_score": best, "likely_member": best >= threshold,
            "best_match": best_src}
    return {"max_score": best, "likely_member": best >= threshold}


_CANDIDATE_RE = None


def _candidate_re():
    global _CANDIDATE_RE
    if _CANDIDATE_RE is None:
        import re
        # secret token core: alnum, masks, separators and password symbols
        tok = r"[A-Za-z0-9*/.!@#%-]*[0-9*!@#%][A-Za-z0-9*/.!@#%-]*"
        # multi-token spans: spaced secrets ("4**2 **0* *3** 7**1") stay one
        # candidate, because every space-separated piece must itself contain
        # a digit or mask char — carrier words ("Ref:", "trend?") break the run
        _CANDIDATE_RE = re.compile(rf"{tok}(?: +{tok})*")
    return _CANDIDATE_RE


def extract_candidates(text: str) -> list[str]:
    """Secret-shaped spans: tokens containing a digit or mask char."""
    return [m for m in _candidate_re().findall(text or "") if len(m) >= 4]


def shape_of(span: str, mask_chars: str = "*") -> str:
    """Structural signature: secret slots (alnum or masked) become `#`.

    Differently-masked variants of one value share a shape (`###-##-####`
    covers `***-**-6789`, `123-**-****` and the full value); compatibility
    then decides merges by known-character agreement, masks matching anything.
    """
    out = []
    for ch in span:
        if ch.isalnum() or ch in mask_chars:
            out.append("#")
        else:
            out.append(ch)
    return "".join(out)


def _compatible(a: str, b: str, mask_chars: str = "*") -> bool:
    """Same shape, no conflicting known characters at any position."""
    if len(a) != len(b) or shape_of(a) != shape_of(b):
        return False
    return all(x == y or x in mask_chars or y in mask_chars
               for x, y in zip(a, b))
