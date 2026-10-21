# Grader: Cross-Model Validation

## Purpose
Verify that deep mode performs cross-model adversarial validation and produces a valid validation log.

## Pass Criteria
1. `.claude/knowledge/cross-model-validation.log.jsonl` exists and is valid JSONL
2. Each record has: `blind_spot_id`, `reviewer`, `model`, `verdict`, `notes`, `additional_blind_spots`, `timestamp`
3. `verdict` is one of: `CONFIRMED`, `REFUTED`, `PARTIAL`, `ADDITIONAL_FINDING`
4. At least 2 reviewers (different model names)
5. At least 1 blind spot has `verdict: CONFIRMED` from ≥2 reviewers
6. If any `verdict: REFUTED`, corresponding blind spot flagged as contradiction
7. `additional_blind_spots` array populated for at least 1 reviewer

## Fail Criteria
- File missing or invalid JSONL
- Missing required fields
- Less than 2 reviewers
- No consensus on any blind spot
- All verdicts same (no adversarial value)

## Evaluation Method
```python
import json

records = []
with open('.claude/knowledge/cross-model-validation.log.jsonl') as f:
    for line in f:
        if line.strip():
            records.append(json.loads(line))

assert len(records) > 0, "No validation records"

required = ["blind_spot_id", "reviewer", "model", "verdict", "notes", "additional_blind_spots", "timestamp"]
for r in records:
    for field in required:
        assert field in r, f"Missing field: {field}"
    assert r["verdict"] in ["CONFIRMED", "REFUTED", "PARTIAL", "ADDITIONAL_FINDING"]

# Check reviewers
reviewers = set(r["reviewer"] for r in records)
models = set(r["model"] for r in records)
assert len(reviewers) >= 2, f"Expected ≥2 reviewers, got {len(reviewers)}"
assert len(models) >= 2, f"Expected ≥2 models, got {len(models)}"

# Check consensus
by_blind_spot = {}
for r in records:
    bs = r["blind_spot_id"]
    if bs not in by_blind_spot:
        by_blind_spot[bs] = []
    by_blind_spot[bs].append(r["verdict"])

consensus_count = 0
for bs, verdicts in by_blind_spot.items():
    confirmed = verdicts.count("CONFIRMED")
    if confirmed >= 2:
        consensus_count += 1

assert consensus_count > 0, "No blind spot with consensus from ≥2 reviewers"

# Check additional findings
additional_total = sum(len(r["additional_blind_spots"]) for r in records)
assert additional_total > 0, "No additional blind spots discovered by reviewers"

print(f"Valid: {len(records)} records, {len(reviewers)} reviewers, {consensus_count} consensus, {additional_total} additional findings")
```