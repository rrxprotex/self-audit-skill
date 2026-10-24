# Grader: domain-layer-valid

Verify `.claude/knowledge/analysis-findings.json` validates against the v1.3
domain-layer schema.

## Pass Criteria

1. File exists and parses as JSON (no `error` marker in the collected artifact).
2. `schema_version == "1"`.
3. `task_resolution.stated_outcome` is a non-empty string.
4. `domain_model.concepts` is a non-empty list (the subject's concept map is seeded).
5. Every finding in `findings` carries the required fields:
   - `id` matches `FIND-NNN` (3+ digits)
   - `statement` non-empty
   - `category_path` non-empty
   - `layer` in `[L1, L2, L3, L4]`
   - `evidence_status` in `[OBSERVED, CANDIDATE, INFERRED, HYPOTHESIS, UNVERIFIED_CLAIM]`
   - `source_refs` is a list (may be empty when `evidence_scope` is stated)
   - `confidence_band` in `[HIGH, MEDIUM, LOW]`
6. Every pattern in `patterns` has `status == "CANDIDATE"` — the eval runs no agent
   context, so lexical nomination can never promote beyond CANDIDATE.
7. `blind_spot_candidates` is non-empty; each entry has non-empty `why_it_matters`
   and `smallest_useful_check` (a named gap must say why it matters and which check
   would settle it).
8. `validation_errors` absent or empty (the embedded schema validation passed).

## Notes

- The fixture workspace (mixed config formats, docs without tests, repeated idioms)
  exercises domain-model seeding, pattern candidacy, and blind-spot nomination.
- Any record with a promoted pattern status or missing honesty fields is a FAIL —
  the schema is the honesty contract.