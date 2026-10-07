# agentic-knowledge-mapper — reconstructed

Inferred build: **multi-agent debate risk scorer**

brief/product/model descriptors -> risk-scoring prompts (tiers 0-100, CVE/attack mapping) -> risk register

- Requests observed: 1207, tokens: 2116937
- Models: {'qwen3.8:27b': 967, 'qwen3.8:latest': 130, 'nomic-embed-text:latest': 109, 'gemma4:31b': 1}
- Query types: {'context-heavy': 302, 'research': 217, 'chat': 214, 'chart/price': 210, 'trade': 142, 'supply': 82, 'mining': 37, 'qa': 2, '(none)': 1}
- Pipeline: make_brief -> score_product_risk -> score_model_risk -> map_attacks(CVE) -> emit_register

## Files
- `inferred_pipeline.py` — runnable scaffold (fill TODO sinks)
- `prompts/template_N.txt` — recovered prompt templates
- `RECONSTRUCTED.json` — machine-readable reconstruction
