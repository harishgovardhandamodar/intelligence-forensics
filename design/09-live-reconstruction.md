# Live reconstruction — tap-driven co-serving (P15–P17)

Static P14 sessions prove what residual surfaces keep. This document covers
the live half: while the tap sniffs Fox-services traffic, every poll
co-serves new completions into the same eight retention policies, so the
Stateless recon views stay warm with real service traffic — retention-only,
never scored.

## Data flow

```mermaid
flowchart TD
    FOX["Fox-services :8210<br/>llm/requests + llm/queue"] --> TAP["LiveTap.poll_once<br/>OUT events with prompt_head"]
    TAP --> FEED["Live tap Feed/Traffic<br/>unchanged"]
    TAP --> COS["tap-driven co-serve<br/>coserve_events per poll"]
    COS --> SURF["residual surfaces<br/>u-live-service users"]
    COS --> COLL["recon_residuals collection<br/>harvest on ingest"]
    SURF --> INSP["residual inspector"]
    SURF --> LREP["live-report<br/>retention + linkage + shapes"]
    COLL --> CONS["consume: scored attack<br/>or unscored read-back"]
```

`poll_once` collects the poll's fresh OUT events and calls `_maybe_coserve`
in a guarded block: reconstruction can never break the tap. Re-polls are
safe (tap-seq dedup); Reset clears records, collection rows, and seq memory
together. Manual `POST /api/recon/coserve` does the same on demand; `POST
/api/recon/coserve-auto` flips the per-poll flag (on by default at tap
start, reported in `/api/live/status`).

## Ethics gate: live users are never scored

```mermaid
flowchart TD
    Q{"truth for u-live-*?"}
    Q -->|register| NO1["refused: ValueError → HTTP 400<br/>live traffic has no ground truth"]
    Q -->|score| NO2["no accuracy keys exist<br/>in live-report by construction"]
    OK["retention counts + linkage<br/>+ candidate shapes"]
    Q --> OK
```

- `register_truth` refuses `u-live-*` (engine `ValueError` → HTTP 400 on
  `/api/recon/begin`).
- `live_report` carries retention per surface, embedding linkage, and
  unscored candidate shapes — a key-walk test asserts no `accuracy` keys.
- `consume` with `attack:true` on a live user 404s with a message that
  points at `attack:false` read-back (never at `begin`, which would 400).
  The UI falls back automatically and renders a "read-back, unscored"
  verdict pointing at the inspector.

## UI wiring

```mermaid
flowchart TD
    TAB["Live tab → Stateless recon subtab"] --> OPEN["loadReconTab + mirror<br/>+ loadLiveUsers + auto co-serve"]
    OPEN --> CARD1["Live traffic card<br/>Co-serve / Harvest only / user picker"]
    OPEN --> CARD2["Live reconstruction card<br/>retention bars + linkage + shapes"]
    OPEN --> CARD3["mirrored P14 cards<br/>KPIs + surfaces + collection + inspector"]
    LOAD["loadLive"] --> THROT["throttled refresh<br/>10 s while visible"]
    THROT --> CARD2
```

The subtab mirrors the dedicated Stateless recon tab (`mirrorReconToLive`,
`l`-prefixed ids): one engine, two views, zero duplicated renderers.

## Framework mapping

`iforensics/sim/recon/live.py` (`enable` / `disable` / `status` /
`report` / `users`) is the framework layer over this wiring; build
instructions live in `to-do-insider-recon-instructions.md`. Mitigations
(`recon/mitigations.py`) apply to co-served rows exactly as to simulated
ones — DLP redaction and retention caps flatten live retention the same way.
