# Simulation scenarios — what each experiment leaks, and how

Two scenario families drive every number in the dashboard. Both use
**synthetic values only** (900-series SSNs, `4242…` PANs, `example.com`,
555 phones, `sk-test-` tokens) and both are bit-reproducible for a fixed
`(scenario, seed, n_turns)`.

- **Embedding-reconstruction sim** (`sim/scenarios/`, 10 workloads) —
  progressive masked disclosure → cosine clustering → position-wise
  assembly. Answers: *how much of a secret leaks through repeated,
  increasingly explicit requests?*
- **Stateless-residual sim** (`iforensics/sim/reconstruction.py`, 3
  workloads) — every turn through eight retention policies (logging,
  billing, vectors, caches, training, infrastructure, support tooling)
  plus the repeat-query amplifier. Answers: *what does a "stateless"
  provider still retain, per surface and pooled?*

The framework mirrors all thirteen under `iforensics/sim/recon/scenarios/`
(3 engine-mapped + 6 generic-builder + live co-serving).

```mermaid
flowchart TD
    CAR["carrier question<br/>long, realistic, paraphrased"] --> MASK["masked secret<br/>Ref: progressive reveal"]
    MASK --> ING["ingest: retention policies<br/>heads, meters, vectors, caches"]
    ING --> SOLO["solo: each surface alone"]
    ING --> CUM["cumulative: pooled prefixes<br/>monotone by construction"]
    ING --> AMP["amplification: one request<br/>vs all requests pooled"]
    SOLO --> REP["report: accuracy +<br/>recovered + coverage"]
    CUM --> REP
    AMP --> REP
```

Disclosure mechanics shared by every scenario: the secret sits at the **end**
of a long carrier (so 180-char heads and 120-char traces genuinely lose it);
masks reveal in thirds/steps; later turns paraphrase the carrier (cosine
clustering stays weak while structural assembly stays strong); every sixth
turn interleaves a secret-free distractor; users periodically re-send a
previous message verbatim (exact-match cache hits).

## Embedding-reconstruction scenarios (`sim/`)

### chatbot_health — patient checkups (`u-health`: ssn, bp)

Repeated health-trend questions with progressive PII disclosure. Short,
highly structured values (SSN `###-##-####`, BP `###/##`) assemble fast —
the baseline every other scenario is compared against.

```mermaid
flowchart LR
    Q["What are my recent health trends?<br/>Ref: 9**-**-****"] --> Q2["same question, Ref: 90*-**-*22*"]
    Q2 --> Q3["paraphrased carrier<br/>Ref: 900-11-2222"]
    Q3 --> ASM["position-wise assembly<br/>known characters win"]
```

### chatbot_financial — disputes (`u-finance`: account_number, credit_card)

Balance and card-link questions. PANs (`4242 #### #### ####`) survive in
dispute-sampled full prompts; account numbers (`####-####-####`) fragment
across meters and traces — partial regimes plateau below 1.0 by design.

```mermaid
flowchart LR
    D["charge dispute + PAN fragment"] --> SAMP["9% dispute sampling<br/>keeps full prompt"]
    D --> MET["meters keep hash only"]
    SAMP --> FULL["full recovery"]
    MET --> PART["partial: hash joins,<br/>no text"]
```

### coding_api_keys — integration help (`u-code`: api_key, aws_key)

`sk-test-…` (24 chars) and `AKIA…` (20 chars) pasted into debugging
threads. Long random alphabets defeat prefix caches but survive anywhere
full text is kept — the avalanche case for never-log-full mitigations.

```mermaid
flowchart LR
    C["boto3 thread + pasted key"] --> CACHE["exact re-send?<br/>full prompt hit"]
    C --> TRACE["trace payload<br/>first 120 chars only"]
    CACHE --> LEAK["key recovered whole"]
    TRACE --> SAFE["key cut off<br/>if pasted late"]
```

### coding_secrets — broken connections (`u-secrets`: db_password, api_key)

Passwords have no internal structure (16 mixed chars), so assembly gets no
shape help — recovery is all-or-nothing per store. Shows why shape grouping
matters: secrets *with* shapes leak gradually, shapeless ones leak wholesale.

```mermaid
flowchart LR
    P["connection string pasted"] --> SHAPE["no shape to group by"]
    SHAPE --> ALL["any full-text store<br/>= total recovery"]
    SHAPE --> NONE["no full-text store<br/>= zero recovery"]
```

### hr_onboarding — new hires (`u-hr`: person_name, home_address, salary, bank_account)

Four-field breadth test. Names/addresses assemble from windows; salary and
bank routing fragment. Measures the framework across heterogeneous shapes
in one session.

```mermaid
flowchart LR
    H["intake forms x4 fields"] --> W["90-char support windows<br/>around each value"]
    H --> EVAL["14% eval sampling"]
    W --> ASM["names + addresses merge"]
    EVAL --> FULL["salary + routing whole"]
```

### support_tickets — triage (`u-support`: email, phone, order_id)

Short identifiers customers paste into tickets. High-exposure surface mix
(support views, snapshots) — the "everything is logged" regime where even
cumulative prefixes saturate early.

```mermaid
flowchart LR
    T["ticket + callback number"] --> OPS["support tooling<br/>12% views, 5% pastes"]
    OPS --> FAST["saturates by<br/>a dozen turns"]
```

### devops_deploy — failing pipelines (`u-devops`: deploy_token, ssh_key, slack_webhook)

Credential-dense threads (tokens, keys, webhook URLs). Webhook URLs carry
structure (`hooks.example.invalid/...`) that assembles across truncated
copies — the staged `tool_use` surface's motivating case.

```mermaid
flowchart LR
    F["failing pipeline + secrets"] --> TR["trace echoes<br/>first 120 chars"]
    F --> Q["over-TTL queue keeps<br/>full prompt 16%"]
    TR --> PART["URL prefix only"]
    Q --> FULL["whole credential"]
```

### legal_contracts — redlines (`u-legal`: deal_value, company, person_name)

Low-structure values (names, amounts) in long clause carriers. Secrets sit
deep inside prose, so head-only stores see almost nothing — the gradient's
low end, where only full-text samplers recover.

```mermaid
flowchart LR
    R["clause + counterparty"] --> HEAD["180-char head<br/>secret beyond cutoff"]
    R --> SNAP["7% snapshots<br/>whole prompt"]
    HEAD --> ZERO["~0 for heads"]
    SNAP --> ONLY["snapshots carry<br/>the session"]
```

### sales_crm — enrichment (`u-sales`: email, phone, deal_value)

Rep-pasted contact PII in short notes. Short carriers mean heads capture
more — inverts the legal_contracts profile and proves carrier length, not
just policy, sets the ceiling.

```mermaid
flowchart LR
    N["short note + contact"] --> HEAD["180-char head<br/>covers most of it"]
    HEAD --> HIGH["heads alone<br/>score high"]
```

### data_engineering — broken ETL (`u-data`: db_conn_string, account_number)

Connection strings mix structure (scheme, host) with randomness (password).
Structured halves assemble; random halves need a full-text store — the
cleanest demo of *partial* recovery as a designed outcome.

```mermaid
flowchart LR
    E["job config pasted"] --> STR["scheme + host<br/>assemble from heads"]
    E --> RND["password segment<br/>needs full text"]
    STR --> P1["partial: topology leaks"]
    RND --> P2["password holds<br/>without full stores"]
```

## Stateless-residual scenarios (P14 engine)

Same disclosure contract, six reveal steps, three workloads. Each runs
through all eight surfaces; reports add solo / cumulative / amplification.

### stateless_chat — health chat (`u-recon-chat`: ssn, bp)

```mermaid
flowchart LR
    C["checkup questions"] --> S8["8 surfaces"]
    S8 --> TRN["training alone:<br/>2/2 at 1.0"]
    S8 --> POOL["pooled: 1.0<br/>amplification +0.79"]
```

### stateless_coding — coding sessions (`u-recon-coding`: api_key, db_password)

```mermaid
flowchart LR
    C["debugging threads"] --> S8["8 surfaces"]
    S8 --> EMB["embeddings: 0.0<br/>linkage only"]
    S8 --> HUM["human_ops: ~1.0<br/>strongest surface"]
```

### stateless_support — support desk (`u-recon-support`: email, phone)

```mermaid
flowchart LR
    D["ticket triage"] --> S8["8 surfaces"]
    S8 --> OPS["support views<br/>dominate recovery"]
```

## Reproduce any scenario

```bash
# embedding sim (full client)
/home/fox/codebase/.venv/bin/python sim/run.py --all
# stateless residual (server-side, persisted + ledgered)
/home/fox/codebase/.venv/bin/python -m iforensics.sim.recon.client.run \
  --server http://localhost:8211 run --scenario stateless_coding --n 48 --seed 42
```

Identical `(scenario, seed, n)` ⇒ identical numbers on any machine.
Complete disclosure reaches 1.0; partial regimes plateau below 1.0 —
both by design, both tested (`iforensics/sim/recon/tests/`).
