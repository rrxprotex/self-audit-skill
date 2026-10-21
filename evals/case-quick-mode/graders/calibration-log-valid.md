# Grader: Calibration Log Valid

## Purpose
Verify that calibration.log.jsonl contains valid calibration records with correct schema and meaningful data.

## Pass Criteria
1. File is valid JSONL (one JSON object per line)
2. Each record has required fields: `assumption_id`, `timestamp`, `prediction`, `actual`, `evidence`, `result`, `confidence_delta`, `new_status`, `layer`, `verification_method`, `session_id`
3. `result` is one of: `CONFIRMED`, `FALSIFIED`, `INCONCLUSIVE`, `SKIPPED`
4. `new_status` matches `result`:
   - `CONFIRMED` → `FACT` or `WORKSPACE_CONVENTION`
   - `FALSIFIED` → `CALIBRATION_ERROR`
   - `INCONCLUSIVE` → `UNVERIFIED_PATTERN`
   - `SKIPPED` → original status
5. `confidence_delta` is a number (negative for falsified, positive for confirmed, ~0 for inconclusive)
6. `layer` is one of: `L1`, `L2`, `L3`, `L4`
7. At least 1 record has `result: FALSIFIED` (calibration error detected)
8. At least 1 record has `result: CONFIRMED` (some assumptions verified)

## Fail Criteria
- Invalid JSONL syntax
- Missing required fields
- Invalid enum values
- No falsified records (skill didn't find any calibration errors)
- No confirmed records (skill didn't verify anything)
- All records have same `confidence_delta` (not actually testing)

## Evaluation Method
```python
import json

records = []
with open('.claude/knowledge/calibration.log.jsonl') as f:
    for line in f:
        if line.strip():
            records.append(json.loads(line))

# Check schema
required = ["assumption_id", "timestamp", "prediction", "actual", "evidence", "result", "confidence_delta", "new_status", "layer", "verification_method", "session_id"]
for r in records:
    for field in required:
        assert field in r, f"Missing field: {field}"
    assert r["result"] in ["CONFIRMED", "FALSIFIED", "INCONCLUSIVE", "SKIPPED"]
    assert r["layer"] in ["L1", "L2", "L3", "L4"]
    assert isinstance(r["confidence_delta"], (int, float))

# Check status mapping
for r in records:
    if r["result"] == "CONFIRMED":
        assert r["new_status"] in ["FACT", "WORKSPACE_CONVENTION"]
    elif r["result"] == "FALSIFIED":
        assert r["new_status"] == "CALIBRATION_ERROR"
    elif r["result"] == "INCONCLUSIVE":
        assert r["new_status"] == "UNVERIFIED_PATTERN"

# Check diversity
falsified = [r for r in records if r["result"] == "FALSIFIED"]
confirmed = [r for r in records if r["result"] == "CONFIRMED"]
assert len(falsified) > 0, "No calibration errors found"
assert len(confirmed) > 0, "No assumptions confirmed"

# Check delta diversity
deltas = [r["confidence_delta"] for r in records]
assert len(set(round(d, 2) for d in deltas)) > 1, "All deltas identical"

print(f"Valid: {len(records)} records, {len(confirmed)} confirmed, {len(falsified)} falsified")
```