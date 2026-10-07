# hive-research-gpu — reconstructed

Inferred build: **paper-surrogate / research-paper summarizer**

paper sections (abstract/figures/experiments) -> section-wise summarization prompts -> surrogates/summaries

- Requests observed: 277, tokens: 318817
- Models: {'nomic-embed-text:latest': 227, 'llama3.2:3b': 38, 'qwen3.8:27b': 12}
- Query types: {'chat': 228, 'research': 27, 'context-heavy': 17, 'chart/price': 5}
- Pipeline: extract_sections -> summarize_section(model) -> summarize_figures -> build_surrogate

## Files
- `inferred_pipeline.py` — runnable scaffold (fill TODO sinks)
- `prompts/template_N.txt` — recovered prompt templates
- `RECONSTRUCTED.json` — machine-readable reconstruction
