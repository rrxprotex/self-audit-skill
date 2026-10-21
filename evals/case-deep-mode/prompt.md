Run self-audit deep mode on this workspace with cross-model validation and historical trend analysis.

The workspace has:
- Multiple calibration sessions in .claude/knowledge/calibration.log.jsonl
- Complex architecture with potential calibration errors
- Domain-specific conventions

Execute the full deep mode pipeline:
1. Phase 0-6: Standard mode full pipeline
2. Cross-model validation: Spawn 2 fresh-context reviewer agents to adversarially verify findings
3. Historical trend analysis: Analyze calibration.log for drift, recurring patterns, improvement
4. Generate enhanced reports: CALIBRATION_TREND_REPORT.md, CROSS_MODEL_VALIDATION.log.jsonl

Expected outputs (in addition to standard mode):
- .claude/knowledge/cross-model-validation.log.jsonl
- .claude/knowledge/calibration-trend-report.md
- Updated calibration-report.md with cross-model and trend sections