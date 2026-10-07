# probe — reconstructed

Inferred build: **probe workload (unclassified)**

prompts -> LLM -> unknown sink (needs more samples)

- Requests observed: 1, tokens: 0
- Models: {'gemma4:31b': 1}
- Query types: {'(none)': 1}
- Pipeline: capture_prompt -> llm.call(model) -> unknown_sink

## Files
- `inferred_pipeline.py` — runnable scaffold (fill TODO sinks)
- `prompts/template_N.txt` — recovered prompt templates
- `RECONSTRUCTED.json` — machine-readable reconstruction
