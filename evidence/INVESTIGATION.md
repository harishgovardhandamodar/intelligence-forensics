# Intelligence Forensics — what the mesh is building

Requests analyzed: **2689** across **7** services.

Mesh peers visible: **2**.
- `axiom-dgx` online=True hw=cpu llm_1h=7 services:[AI-Research-Workbench, Go-Quai-Radar, Go-fox-agentic-trader, Knowledgebase, Ollama-local-hives-cluster, Quai-Network-analytics, Quai-RADAR, agentic-knowledge-mapper, agentic-trade, finance-study, fox-agentic-trader, fox-analytics]
- `harishs-macbook-pro-1` online=True hw=mlx llm_1h=0 services:[]

## agentic-knowledge-mapper
Inferred build: **multi-agent debate risk scorer**
brief/product/model descriptors -> risk-scoring prompts (tiers 0-100, CVE/attack mapping) -> risk register
- requests: 1207, tokens: 2116937 (avg 1753.9/req), cadence ~828.0s
- window: 2026-09-24T08:05:15 -> 2026-10-05T21:28:43
- models: `{'qwen3.8:27b': 967, 'qwen3.8:latest': 130, 'nomic-embed-text:latest': 109, 'gemma4:31b': 1}`
- query types: `{'context-heavy': 302, 'research': 217, 'chat': 214, 'chart/price': 210, 'trade': 142, 'supply': 82, 'mining': 37, 'qa': 2, '(none)': 1}` / requestors: `{'user': 1207}`
- pipeline: `make_brief -> score_product_risk -> score_model_risk -> map_attacks(CVE) -> emit_register`
- schema hints: ['brief', 'exposure tier', 'knowledge graph', 'misuse potential', 'model risk', 'residual risk', 'schema']
- recovered instructions:
  - Product: multi-agent debate systems (safety, robustness, and operational risks)
  - Model: multi-agent debate methods (LLM-based and beyond)
  - Model: multi-agent debate methods (LLM-based and beyond) (model)
  - Title: Risks and failure modes of multi-agent debate systems
  - Brief: Enumerate documented and hypothesized risks: sycophancy and conformity pressure among agents, collusion or echo-chamber dynamics, prompt-injection amplification across agents, resource/compute blow-up, adversarial
  - Title: Multi-agent debate methods: architectures, variants, and empirical results
- prompt templates observed:
  - (x333) Model: {{model_desc}}
  - (x263) Brief: {{brief}}
  - (x125) Product: {{product}}
  - (x43) Question: what level of memorization by these network is plausible, what would be the closest reconstruction plausible ? is it possible to use this synthetic data by a party who has major share in data trained to reconst

## quai-radar
Inferred build: **blockchain-news knowledge-graph extractor**
ingests news items (title+content) -> LLM extracts structured KG facts -> writes graph nodes/edges
- requests: 1145, tokens: 1797921 (avg 1570.2/req), cadence ~1954.2s
- window: 2026-09-11T14:55:21 -> 2026-10-07T11:54:48
- models: `{'qwen3.8:latest': 1145}`
- query types: `{'(none)': 821, 'chart/price': 322, 'research': 2}` / requestors: `{'user': 1145}`
- pipeline: `ingest_feed -> build_kg_prompt(title, content) -> llm.extract(model) -> parse_facts -> upsert_graph`
- schema hints: ['brief', 'digest', 'implications for quai', 'knowledge graph', 'schema', 'structured facts', 'tutor', 'what to watch']
- recovered instructions:
  - You are a blockchain research analyst. Extract structured facts about the item below for a knowledge graph. Base everything ONLY on the item's title and content. Do not repeat the schema back — produce the actual facts.
  - TITLE: ‘Old money’ has stronger Bitcoin ‘diamond hands,’ says BingX
  - TITLE: Wall Street wealth creation model is unsustainable for most
  - TITLE: Trump-backed WLFI plans USD1 payments for online businesses
  - TITLE: Crypto card access doesn’t match global demand, Tangem says
  - TITLE: Finland orders halt to work on two Google data centres
- prompt templates observed:
  - (x1061) You are a blockchain research analyst. Extract structured facts about the item below for a knowledge graph. Base everything ONLY on the item's title and content. Do not repeat the schema back — produce the actual facts. | 
  - (x24) PROJECT DATA GROUNDING (real, citable data from the Quai-RADAR dashboard): |  | LIVE MARKET: QUAI $0.010087544223399685 · QI $0.7875559257826807 (cross $1.1050992885383195) · WQI/QUAI rate 0.009128179094877679 · data age 1.7
  - (x6) You are Fox writing the daily research brief for the Quai Network intelligence dashboard. Based ONLY on the digest below (what's new in the research landscape, news, market and the swarm-protocol regime/gates), write a c
  - (x4) PROJECT DATA GROUNDING (real, citable data from the Quai-RADAR dashboard): |  | LIVE MARKET: QUAI $0.009054467008212618 · QI $1.132035890098335 (cross $1.056700316653958) · WQI/QUAI rate 0.008568623350926582 · data age 1.597

## hive-research-gpu
Inferred build: **paper-surrogate / research-paper summarizer**
paper sections (abstract/figures/experiments) -> section-wise summarization prompts -> surrogates/summaries
- requests: 277, tokens: 318817 (avg 1151.0/req), cadence ~38.4s
- window: 2026-10-05T19:19:24 -> 2026-10-05T22:15:51
- models: `{'nomic-embed-text:latest': 227, 'llama3.2:3b': 38, 'qwen3.8:27b': 12}`
- query types: `{'chat': 228, 'research': 27, 'context-heavy': 17, 'chart/price': 5}` / requestors: `{'subagent': 277}`
- pipeline: `extract_sections -> summarize_section(model) -> summarize_figures -> build_surrogate`
- schema hints: ['abstract', 'brief', 'experimental setup', 'figures available', 'knowledge graph', 'research questions']
- recovered instructions:
  - Title: From Model-Based Screening to Data-Driven Surrogates: A Multi-Stage Workflow for Exploring Stochastic Agent-Based Models
  - Title: SWE-Debate: Competitive Multi-Agent Debate for Software Issue Resolution
  - Title: AOAD-MAT: Transformer-based multi-agent deep reinforcement learning model considering agents' order of action decisions
  - Title: A Review of Cooperative Multi-Agent Deep Reinforcement Learn
  - Title: Augmenting the action space with conventions to improve multi-agent cooperation in Hanabi
  - Title: A Methodology to Engineer and Validate Dynamic Multi-level Multi-agent Based Simulations
- prompt templates observed:
  - (x27) Title: {{paper_title}}
  - (x4) Paper: {{paper}}
  - (x2) Answer using ONLY the numbered context excerpts provided. Cite every claim with its excerpt number like [1] or [2][5]. If the context is insufficient, say exactly what is missing instead of guessing. |  | Write a thorough re
  - (x2) You drafted a partial research answer. List up to 3 specific information gaps as refined arXiv-style search queries. Return JSON: {"queries": ["..."]} |  | Question: Summarize the state of multi-agent debate methods | Draft:

## kid-learning-lab
Inferred build: **tutor / learning-lab skill coach**
skill+learner-state -> pedagogical prompts (teach/clue/investigate/challenge) -> tutor turn
- requests: 37, tokens: 2363 (avg 63.9/req), cadence ~243.7s
- window: 2026-09-23T15:23:42 -> 2026-09-23T17:49:56
- models: `{'nomic-embed-text:latest': 32, 'gemma4:31b': 5}`
- query types: `{'(none)': 37}` / requestors: `{'user': 37}`
- pipeline: `learner_state -> render_skill_prompt -> llm.coach(embed_model|chat) -> next_step`
- schema hints: ['check question', 'guiding question', 'skill:', 'subject:', 'tutor']
- recovered instructions:
  - Task: Teach the skill like a patient tutor: define it simply, walk through the example step by step, then give one quick check question.
  - Task: Give a short clue, never the answer. Ask one guiding question.
  - Task: Invite one thoughtful question and one possible way to investigate it. Do not give a quiz answer.
  - Task: Act as Prof. Fox. Explain concepts simply, use a small example, ask one check-for-understanding question, and guide the learner without doing all the thinking for them.
  - Task: Suggest one next challenge that is slightly harder and explain why in one sentence.
  - Task: Give a warm, specific reflection prompt that helps a child notice their strategy.
- prompt templates observed:
  - (x26) Subject: {{subject}}
  - (x4) Give one short hint about fractions without giving the answer.
  - (x2) Say hi in five words.
  - (x2) hi

## gateway-unknown
Inferred build: **gateway-unknown workload (unclassified)**
prompts -> LLM -> unknown sink (needs more samples)
- requests: 21, tokens: 161 (avg 7.7/req), cadence ~49552.5s
- window: 2026-09-24T08:01:56 -> 2026-10-05T19:19:26
- models: `{'nomic-embed-text:latest': 10, 'qwen3.8:latest': 5, 'unknown': 2, 'llama3.2:3b': 2, 'qwen3.8:27b': 1, 'gemma4:31b': 1}`
- query types: `{'(none)': 11, 'chat': 10}` / requestors: `{'user': 21}`
- pipeline: `capture_prompt -> llm.call(model) -> unknown_sink`
- schema hints: []
- recovered instructions:
- prompt templates observed:
  - (x13) hi
  - (x4) say hi
  - (x1) Reply with the single word: ready

## probe
Inferred build: **probe workload (unclassified)**
prompts -> LLM -> unknown sink (needs more samples)
- requests: 1, tokens: 0 (avg 0.0/req), cadence ~0s
- window: 2026-09-24T08:23:36 -> 2026-09-24T08:23:36
- models: `{'gemma4:31b': 1}`
- query types: `{'(none)': 1}` / requestors: `{'user': 1}`
- pipeline: `capture_prompt -> llm.call(model) -> unknown_sink`
- schema hints: []
- recovered instructions:
- prompt templates observed:
  - (x1) Reply with exactly: routed

## warmup
Inferred build: **warmup workload (unclassified)**
prompts -> LLM -> unknown sink (needs more samples)
- requests: 1, tokens: 0 (avg 0.0/req), cadence ~0s
- window: 2026-09-24T08:01:47 -> 2026-09-24T08:01:47
- models: `{'nomic-embed-text:latest': 1}`
- query types: `{'(none)': 1}` / requestors: `{'user': 1}`
- pipeline: `capture_prompt -> llm.call(model) -> unknown_sink`
- schema hints: []
- recovered instructions:
- prompt templates observed:
  - (x1) Reply with exactly: warm

_Caveat: fox DB stores truncated, secret-redacted, PII-masked prompt heads; completions are not logged. Reconstruction recovers templates + pipeline, not exact source._