# gateway-unknown — reconstructed

Inferred build: **gateway-unknown workload (unclassified)**

prompts -> LLM -> unknown sink (needs more samples)

- Requests observed: 21, tokens: 161
- Models: {'nomic-embed-text:latest': 10, 'qwen3.8:latest': 5, 'unknown': 2, 'llama3.2:3b': 2, 'qwen3.8:27b': 1, 'gemma4:31b': 1}
- Query types: {'(none)': 11, 'chat': 10}
- Pipeline: capture_prompt -> llm.call(model) -> unknown_sink

## Files
- `inferred_pipeline.py` — runnable scaffold (fill TODO sinks)
- `prompts/template_N.txt` — recovered prompt templates
- `RECONSTRUCTED.json` — machine-readable reconstruction
