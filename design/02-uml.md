# 02 — UML structure

Which module owns which responsibility, and how they depend. One FastAPI app
(`dashboard.py`) plus a flat `iforensics/` package: every capability is a
module with a narrow job; `dashboard.py` and `cli.py` are the only wiring.

Related: [01-system-context.md](01-system-context.md) ·
[interaction.md](interaction.md) · [data-model.md](data-model.md)

## Components: who owns what

```mermaid
flowchart TB
    subgraph HTTP["HTTP + CLI surface"]
        DASH["dashboard.py<br/>~25 routes · inline SPA"]
        CLI["cli.py<br/>investigate · build · agent-run<br/>progression · dashboard"]
    end
    subgraph COLLECT["Collect (read-only)"]
        FX["fox_client.py<br/>urllib probes of :8210"]
        ST["store.py<br/>API dump + WAL-safe DB copy"]
        CFG["config.py<br/>URLs · dirs · candidates"]
    end
    subgraph HEUR["Heuristic investigator (no LLM)"]
        FP["fingerprints.py<br/>template clustering"]
        INF["infer.py<br/>rules → project + pipeline"]
        PRG["progression.py<br/>time slices + deltas"]
        SCO["score.py<br/>reconstruction score<br/>vibe index"]
    end
    subgraph AGENT["Agentic investigator (local LLM)"]
        OLL["ollama_client.py<br/>stdlib /api/chat · think:false"]
        AGT["agents.py<br/>scout · profiler · critic<br/>reporter · background runs"]
        RVZ["run_viz.py<br/>DAG · costs · agreement"]
    end
    subgraph OUT["Outputs"]
        REC["reconstruct.py<br/>scaffolds per service"]
        REP["report.py<br/>INVESTIGATION.md"]
        DD["design_docs.py<br/>fixed-index doc server"]
    end
    DASH --> FX
    DASH --> ST
    DASH --> DD
    DASH --> RVZ
    CLI --> ST
    CLI --> INF
    CLI --> AGT
    ST --> CFG
    FX --> CFG
    INF --> FP
    PRG --> INF
    SCO --> INF
    AGT --> OLL
    RVZ --> AGT
    CLI --> REC
```

Dependency rule: heuristic modules never import the LLM client; the LLM client
never touches the database (agents receive rows, never a path); outputs never
import collectors. Information flows one way: collect → infer → present.

## Class sketch: the agent run

```mermaid
classDiagram
    class AgentRun {
        +run_id: str
        +model: qwen3.8:27b
        +quick: bool
        +services: list
        +elapsed_s: float
    }
    class AgentOutput {
        +agent: str
        +content: str
        +parsed: dict
        +prompt_tokens: int
        +completion_tokens: int
        +ms: float
    }
    class ServiceProfile {
        +project: str
        +pipeline: list
        +models: dict
        +fingerprint: dict
    }
    class ScoredStep {
        +requests: int
        +score: float
        +grade: str
        +vibe: float
        +delta: dict
    }
    AgentRun "1" *-- "0..n" AgentOutput : profilers/critics
    AgentRun "1" *-- "1" AgentOutput : scout + reporter
    ServiceProfile "1" --> "0..n" ScoredStep : progression slices
```
