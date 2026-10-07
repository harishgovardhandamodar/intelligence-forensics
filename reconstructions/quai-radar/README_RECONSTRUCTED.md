# quai-radar — reconstructed

Inferred build: **blockchain-news knowledge-graph extractor**

ingests news items (title+content) -> LLM extracts structured KG facts -> writes graph nodes/edges

- Requests observed: 1145, tokens: 1797921
- Models: {'qwen3.8:latest': 1145}
- Query types: {'(none)': 821, 'chart/price': 322, 'research': 2}
- Pipeline: ingest_feed -> build_kg_prompt(title, content) -> llm.extract(model) -> parse_facts -> upsert_graph

## Files
- `inferred_pipeline.py` — runnable scaffold (fill TODO sinks)
- `prompts/template_N.txt` — recovered prompt templates
- `RECONSTRUCTED.json` — machine-readable reconstruction
