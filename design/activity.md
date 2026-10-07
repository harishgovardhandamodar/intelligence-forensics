# 04 — Activity

The decisions the pipeline makes: which rows count, when a label sticks, when
a run is trustworthy, and when the UI degrades instead of failing.

Related: [interaction.md](interaction.md) · [02-uml.md](02-uml.md)

## Investigation lifecycle: from queries to verdict

```mermaid
flowchart TB
    S0["rows available?<br/>newest evidence DB"]
    S0 -->|no| E0["503 + honest error<br/>(never empty charts)"]
    S0 -->|yes| S1["profile per service<br/>rules over templates"]
    S1 --> S2{"label stable<br/>across slices?"}
    S2 -->|yes, ≥2 steps| V1["converged=true<br/>score gains weight"]
    S2 -->|flips| V0["converged=false<br/>partial views kept visible"]
    S1 --> S3{"evidence volume?"}
    S3 -->|≥~200 queries| G1["grade A/B<br/>rebuild with confidence"]
    S3 -->|<40 queries| G0["grade C/D<br/>show, flag thin evidence"]
    V1 --> DONE["scaffold + report"]
    V0 --> DONE
    G1 --> DONE
    G0 --> DONE
```

## Agent-run decisions

```mermaid
flowchart TB
    R0["agent-run requested"]
    R0 --> P0{"Ollama ping ok?"}
    P0 -->|no| E1["abort before touching evidence<br/>no half-runs"]
    P0 -->|yes| R1["scout ranks (≤512 tok)"]
    R1 --> R2["profilers ×N threaded (≤768 tok)<br/>JSON parse or raw-fallback"]
    R2 --> Q0{"quick?"}
    Q0 -->|yes| R4["reporter (raw+heuristic fallback)<br/>never fed empty {}"]
    Q0 -->|no| R3["critics ×N (≤256 tok)<br/>gaps extraction"]
    R3 --> R4
    R4 --> R5["manifest + BRIEF.md<br/>errors listed, never hidden"]
```

Two rules learned the hard way and now encoded: token budgets floor at the
size the JSON actually needs (truncated JSON parses to nothing), and the
reporter is never fed empty parses — it falls back to raw output plus the
heuristic label, so a cascade failure becomes a weaker brief, not fiction.

## UI degradation ladder

```mermaid
flowchart LR
    L0["endpoint slow"] --> L1["section shows its own error<br/>rest of page renders"]
    L1 --> L2["mermaid CDN blocked"]
    L2 --> L3["diagram shown as source<br/>content never hidden"]
    L3 --> L4["fox down"]
    L4 --> L5["overview says 'down', evidence still browsable"]
```
