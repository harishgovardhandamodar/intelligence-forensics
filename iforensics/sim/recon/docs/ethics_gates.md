# Ethics gates (from `design/ethics.md`, applied to this framework)

```
new work?
 │  synthetic-only? ──no──▶ STOP. No real prompts, no real PII, ever.
 │  yes
 ▼
reserved ranges only? ──no──▶ STOP. check_reserved() must pass.
 │  yes
 ▼
insider view sees truth? ──yes──▶ STOP. TruthRegistry is server-side;
 │  no                         the insider gets residuals + linkage only.
 ▼
vectors claimed as text? ──yes──▶ STOP. text accuracy is 0, always.
 │  no
 ▼
live traffic scored? ──yes──▶ STOP. retention counts only, no accuracy.
 │  no
 ▼
report carries score + coverage + caveats? ──no──▶ STOP. Add them.
 │  yes
 ▼
ledger entry appended + verifiable? ──no──▶ STOP. Append, then publish.
 │  yes
 ▼
PROCEED. Publish the report with the non-claims attached.
```

`design/privacy.md`: minimization applies to the framework too — harvest
what the policy keeps, nothing more; purge on reset; per-user scoping on
every read. `design/trust-boundaries.md`: the dashboard never names a
non-loopback host in code (T2); the CLI takes the server address as an
argument, never a constant.
