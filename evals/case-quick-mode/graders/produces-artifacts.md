# Grader: Produces Artifacts

## Purpose
Verify that self-audit quick mode produces all required output artifacts in the correct locations.

## Pass Criteria
All of the following files MUST exist after skill execution:
- `.claude/knowledge/workspace-model.md`
- `.claude/knowledge/assumptions.json`
- `.claude/knowledge/calibration.log.jsonl`
- `.claude/knowledge/blind-spots.md`
- `.claude/knowledge/calibration-report.md`
- `.claude/knowledge/calibration-summary.json`

Each file MUST be non-empty and valid for its format (markdown or JSON/JSONL).

## Fail Criteria
- Any required file missing
- Any file empty
- JSON/JSONL files invalid syntax
- Markdown files contain only template placeholders

## Evaluation Method
```bash
# Check all files exist and are non-empty
for f in workspace-model.md assumptions.json calibration.log.jsonl blind-spots.md calibration-report.md calibration-summary.json; do
  if [ ! -s ".claude/knowledge/$f" ]; then
    echo "MISSING OR EMPTY: $f"
    exit 1
  fi
done

# Validate JSON/JSONL
python -c "import json; [json.loads(l) for l in open('.claude/knowledge/calibration.log.jsonl')]"
python -c "import json; json.load(open('.claude/knowledge/assumptions.json'))"
python -c "import json; json.load(open('.claude/knowledge/calibration-summary.json'))"

echo "All artifacts present and valid"
```