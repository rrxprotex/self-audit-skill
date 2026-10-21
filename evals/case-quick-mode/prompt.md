Run self-audit quick mode on this workspace. Produce calibration report and top 5 blind spots.

The workspace has:
- Python project with pytest tests
- Standard directory structure (src/, tests/, docs/)
- Some implicit conventions around error handling and config

Execute the full quick mode pipeline:
1. Phase 0: Map workspace (inventory, stack detection, convention sampling)
2. Phase 1: Extract top 20 assumptions with confidence scores
3. Phase 2: Test critical assumptions (L3/L4) against evidence
4. Phase 3: Map blind spots, rank top 5 by risk
5. Phase 6: Generate calibration report with summary statistics

Expected outputs:
- .claude/knowledge/workspace-model.md
- .claude/knowledge/assumptions.json
- .claude/knowledge/calibration.log.jsonl (append)
- .claude/knowledge/blind-spots.md
- .claude/knowledge/calibration-report.md
- .claude/knowledge/calibration-summary.json