# kid-learning-lab — reconstructed

Inferred build: **tutor / learning-lab skill coach**

skill+learner-state -> pedagogical prompts (teach/clue/investigate/challenge) -> tutor turn

- Requests observed: 37, tokens: 2363
- Models: {'nomic-embed-text:latest': 32, 'gemma4:31b': 5}
- Query types: {'(none)': 37}
- Pipeline: learner_state -> render_skill_prompt -> llm.coach(embed_model|chat) -> next_step

## Files
- `inferred_pipeline.py` — runnable scaffold (fill TODO sinks)
- `prompts/template_N.txt` — recovered prompt templates
- `RECONSTRUCTED.json` — machine-readable reconstruction
