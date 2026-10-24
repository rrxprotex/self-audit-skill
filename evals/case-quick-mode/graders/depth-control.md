# Grader: depth-control

Verify quick mode honors depth rules: it must NOT pay for the domain layer's
expensive parts.

## Pass Criteria

1. `.claude/knowledge/analysis-findings.json` exists in the quick-mode run.
2. The report has **no `domain_model` key** (absent key, not an empty object).
3. The report has **no `patterns` key** (absent key, not an empty array).
4. The report still carries `task_resolution`, `findings`, and
   `blind_spot_candidates` (quick keeps the cheap parts).

## Notes

- Depth mapping (`analysis_depth("quick", …)`): `domain_model=False`,
  `pattern_discovery=False`, `blind_spot_search=True`, `task_resolution=True`.
- This is the observable proof that simple tasks stay short: the file is
  written but the expensive analysis sections are structurally absent.