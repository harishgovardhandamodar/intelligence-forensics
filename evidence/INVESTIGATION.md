# Intelligence Forensics — what the mesh is building

Requests analyzed: **2720** across **8** services.

Mesh peers visible: **2**.
- `axiom-dgx` online=True hw=cpu llm_1h=0 services:[AI-Research-Workbench, Go-Quai-Radar, Go-fox-agentic-trader, Knowledgebase, Ollama-local-hives-cluster, Quai-Network-analytics, Quai-RADAR, agentic-knowledge-mapper, agentic-trade, finance-study, fox-agentic-trader, fox-analytics]
- `harishs-macbook-pro-1` online=True hw=mlx llm_1h=0 services:[]

## agentic-knowledge-mapper
Inferred build: **multi-agent debate risk scorer**
brief/product/model descriptors -> risk-scoring prompts (tiers 0-100, CVE/attack mapping) -> risk register
- requests: 1226, tokens: 2200581 (avg 1794.9/req), cadence ~932.9s
- window: 2026-09-24T08:05:15 -> 2026-10-07T13:32:07
- models: `{'qwen3.8:27b': 986, 'qwen3.8:latest': 130, 'nomic-embed-text:latest': 109, 'gemma4:31b': 1}`
- query types: `{'context-heavy': 302, 'research': 217, 'chat': 214, 'chart/price': 210, 'trade': 161, 'supply': 82, 'mining': 37, 'qa': 2, '(none)': 1}` / requestors: `{'user': 1226}`
- pipeline: `make_brief -> score_product_risk -> score_model_risk -> map_attacks(CVE) -> emit_register`
- schema hints: ['brief', 'exposure tier', 'knowledge graph', 'misuse potential', 'model risk', 'residual risk', 'schema']
- recovered instructions:
  - Title: Risks and failure modes of multi-agent debate systems
  - Brief: Enumerate documented and hypothesized risks: sycophancy and conformity pressure among agents, collusion or echo-chamber dynamics, prompt-injection amplification across agents, resource/compute blow-up, adversarial
  - Product: multi-agent debate systems (safety, robustness, and operational risks)
  - Model: multi-agent debate methods (LLM-based and beyond)
  - Model: multi-agent debate methods (LLM-based and beyond) (model)
  - Title: Multi-agent debate methods: architectures, variants, and empirical results
- prompt templates observed:
  - (x128) Brief: {{brief}}
  - (x125) Product: {{product}} | Use case:  | Exposure tier: confidential_data | Subject profile: no model-specific signals; assess as described | Declared controls already in place: none | Evidence snippets: none |  | Control catalogue: | - C01 
  - (x77) Brief: {{brief}} | Description: x
  - (x74) Model: {{model_desc}} | Use: what adversarial scenarios could an attacker engineer with this model for credit scoring of tabular records | Profile: foundation model over tabular records no conversational surface | Interface: n

## quai-radar
Inferred build: **blockchain-news knowledge-graph extractor**
ingests news items (title+content) -> LLM extracts structured KG facts -> writes graph nodes/edges
- requests: 1151, tokens: 1803855 (avg 1567.2/req), cadence ~1948.8s
- window: 2026-09-11T14:55:21 -> 2026-10-07T13:28:06
- models: `{'qwen3.8:latest': 1151}`
- query types: `{'(none)': 821, 'chart/price': 328, 'research': 2}` / requestors: `{'user': 1151}`
- pipeline: `ingest_feed -> build_kg_prompt(title, content) -> llm.extract(model) -> parse_facts -> upsert_graph`
- schema hints: ['brief', 'digest', 'implications for quai', 'knowledge graph', 'schema', 'structured facts', 'tutor', 'what to watch']
- recovered instructions:
  - You are a blockchain research analyst. Extract structured facts about the item below for a knowledge graph. Live tap check.
  - TITLE: Fundamental CRB-Rate Tradeoff of Rydberg Atomic Receivers fo
  - TITLE: Keeping the interaction structure explicit: comment on ''Gra
  - TITLE: Disentangling Paradigm, Identifier, and Decoding in Generati
  - TITLE: RIS-Assisted Reliability Maximization for URLLC in Upper Mid
  - TITLE: Rapid Fredholm stabilization of the Kuramoto--Sivashinsky eq
- prompt templates observed:
  - (x1066) You are a blockchain research analyst. Extract structured facts about the item below for a knowledge graph. Base everything ONLY on the item's title and content. Do not repeat the schema back — produce the actual facts. | 
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
  - (x5) Title: {{paper_title}} |  | ## abstract | AOAD-MAT: Transformer-based Multi-Agent | Deep Reinforcement Learning Model considering | Agents’ Order of Action Decisions ⋆ | Shota Takayama and Katsuhide Fujita | Graduate School of Enginee
  - (x4) Title: {{paper_title}} |  | ## abstract | From Model-Based Screening to Data-Driven | Surrogates: A Multi-Stage Workflow for | Exploring Stochastic Agent-Based Models | Paul Saves1[0000−0001−5889−2302], Matthieu Mastio1[0009−0002−34
  - (x4) Title: {{paper_title}} |  | ## abstract | Augmenting the action space with conventions to | improve multi-agent cooperation in Hanabi | F. Bredell1*, H. A. Engelbrecht1 and J. C. Schoeman1 | 1*Electrical and Electronic Engineering, 
  - (x3) Title: {{paper_title}} |  | ## abstract | SWE-Debate: Competitive Multi-Agent Debate for Software Issue | Resolution | Han Li† | Shanghai Jiao Tong University | China | lih***u.cn | Yuling Shi† | Shanghai Jiao Tong University | China | yul***u.

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
  - (x26) Subject: {{subject}} | Skill: {{skill}} | Task: {{task}} | Context: {{context}}
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

## live-selftest
Inferred build: **live-selftest workload (unclassified)**
prompts -> LLM -> unknown sink (needs more samples)
- requests: 6, tokens: 299 (avg 49.8/req), cadence ~3.9s
- window: 2026-10-07T13:15:56 -> 2026-10-07T13:16:15
- models: `{'qwen3.8:27b': 6}`
- query types: `{'trade': 5, 'chat': 1}` / requestors: `{'user': 6}`
- pipeline: `capture_prompt -> llm.call(model) -> unknown_sink`
- schema hints: ['brief']
- recovered instructions:
- prompt templates observed:
  - (x1) Live probe 5: multi-agent debate risk brief
  - (x1) Live probe 4: multi-agent debate risk brief
  - (x1) Live probe 3: multi-agent debate risk brief
  - (x1) Live probe 2: multi-agent debate risk brief

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