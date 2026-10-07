"""Progressive query construction (P8.1): how one secret leaks piece by piece.

A scenario is a base prompt plus a reveal schedule: each step discloses more
unmasked characters of the same value (mask char `*`):

    step 0:  "***-**-6789"
    step 1:  "123-**-****"
    step 2:  "***-45-6789"   -> assembled: "123-45-6789"

`mask_schedule` derives that schedule deterministically from the value:
split into thirds, reveal one new third per step while keeping whatever was
already revealed. Near-duplicate variants (reorder, synonym swap, filler)
keep cosine similarity high while changing surface text — the attack must
work on meaning, not string equality.
"""
from __future__ import annotations

MASK = "*"

FILLERS = ["Please help me with this: ", "Quick question — ", "Hi, ",
           "Following up on my last message. "]


def mask_schedule(value: str, steps: int = 3,
                  complete: bool = True) -> list[str]:
    """Reveal schedule for a value: thirds disclosed progressively.

    Non-alphanumeric separators stay visible (they carry no secret); every
    step keeps previously revealed characters. With complete=False the final
    alphanumeric slot stays masked forever — the partial-recovery regime,
    where the curve plateaus below 1.0.
    """
    slots = [i for i, ch in enumerate(value) if ch.isalnum()]
    if not slots or steps < 1:
        return ["".join(MASK if c.isalnum() else c for c in value)]
    out, revealed = [], set()
    thirds = [slots[i::steps] for i in range(steps)]
    hold = set() if complete else {slots[-1]}
    for step in range(steps):
        revealed.update(thirds[step])
        shown = revealed - hold
        out.append("".join(c if (not c.isalnum() or i in shown) else MASK
                           for i, c in enumerate(value)))
    return out


def build_progressive(base_prompt: str, secret_value: str,
                      steps: int = 3, complete: bool = True) -> list[dict]:
    """Prompt/mask pairs whose masks assemble to the full value."""
    return [{"prompt": f"{base_prompt} Ref: {mask}",
             "mask": mask, "step": i}
            for i, mask in enumerate(mask_schedule(secret_value, steps,
                                                   complete))]


def near_duplicates(text: str, seed: int | None = None) -> list[str]:
    """Deterministic surface variants that preserve meaning.

    Returns [original, reordered-words, synonym-swapped, filler-prefixed].
    """
    import random
    rng = random.Random(seed)
    words = text.split()
    variants = [text]
    if len(words) > 3:
        mid = words[1:-1]
        rng.shuffle(mid)
        variants.append(" ".join([words[0]] + mid + [words[-1]]))
    else:
        variants.append(text + " please")
    swaps = {"What": "Could you tell me", "How": "In what way",
             "my": "the", "please": "kindly", "connect": "link up",
             "balance": "remaining funds", "trend": "pattern over time"}
    variants.append(" ".join(swaps.get(w, w) for w in words))
    variants.append(rng.choice(FILLERS) + text[0].lower() + text[1:])
    return variants
