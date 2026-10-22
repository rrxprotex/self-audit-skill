# Changelog

All notable changes to this project will be documented in this file.

The format is based on [Keep a Changelog](https://keepachangelog.com/en/1.0.0/),
and this project adheres to [Semantic Versioning](https://semver.org/spec/v2.0.0.html).

## [1.2.0] - 2026-10-23

Competitive-superset release: everything the best external calibration skills do, on top of the quantitative system. The status/result enums, L1–L4 layers, USER_* model, learning-unit lifecycle, and cross-model/trend machinery are unchanged — this release adds rigor around them.

### Added
- **Scope, Stakes & Target (§7)**: a two-line scope statement before any inventory — `--target workspace|plan|diff|last-answer` plus the decision the audit serves. `--stakes low|medium|high` sets the verification budget (stakes-cap-wins at `high`) and picks the default mode. New `--target` / `--stakes` CLI flags and `SELF_AUDIT_TARGET` / `SELF_AUDIT_STAKES` env vars.
- **Provenance & evidence cutoff (§1)**: every claim carries `provenance: OBSERVED_THIS_SESSION|INFERRED|RECALLED|ASSUMED` and `verified_this_session`; FACT only from this session's tool output. Loaded memory/prior logs enter as beliefs and are re-verified, never auto-upgraded.
- **Negative-search discipline (§4)**: `search_scope` is required for search-based tests ("not found in scope S", never "doesn't exist"); unscoped searches run as `INCONCLUSIVE`/`check_status: BLOCKED`; a null counterexample search yields scoped `CONFIRMED` worded "no counterexamples in <scope>", capped at `WORKSPACE_CONVENTION` — never automatic FACT at 1.0.
- **Cheapest decisive check + disconfirmation preference (§4)**: the claim's `falsifier` defines the probe; confirm-only checks aren't verification. New verification recipes 6–7 (recalled-version cross-check, flag/API existence).
- **Measurement split (§2)**: numeric confidence only for calibration-log entries (it is measured against outcomes); unmeasured claims carry HIGH/MEDIUM/LOW bands. Decorative numbers banned.
- **Pre-Mortem Protocol** in **all** modes: exactly three items, one decisive check each; deep adds a cross-model attack extension.
- **Five probe questions** (preconditions / evidence / falsifier / edge cases unexamined / possible confusions) captured as Phase 1 fields; `claim_kind` taxonomy; verification priority = impact × (1 − confidence), top-N ∪ load-bearing.
- **Coverage Ledger**: Opened / Seen-only / Never-touched + commands ran vs. assumed; the ordering invariant (no Phase 2 probe on an unmapped, unregistered surface).
- **Fix Mode & Write Policy (two zones)**: writes only to knowledge/memory roots; audited workspace read-only; fix mode only on explicit request, with per-change approval and post-fix re-verification.
- **Report redesign**: Bottom Line first, then Corrected Beliefs, Claims Table (tier/provenance/band+score), Top Blind Spots, Coverage Gaps & Scope Limits, unconditional Still Unverified, gate-filtered Open Questions, 4-bucket Epistemic Buckets + value-ordered Recommended Probes, Stop Reason; statistics/trend/cross-model move to an appendix. Quick-mode minimum set defined.
- **Stop conditions STOP F/G/H**: empty-workspace early stop; the G+H stopping rule (load-bearing verified-or-labeled AND cost exceeds decision value) with a high-stakes caveat; three-part closing (inspected / unknown / out of scope) including zero-findings audits.
- **Anti-Patterns #11–#20**: fabrication across every record field, self-authorized remediation, intuition-directed sweep, filler findings, filename-implies-content, assumed command/flag behavior, unexplained inference, stale conclusion restatement (`finding_kind: STALE_BASIS`), speculation-as-defect, secrets/scope violations.
- **Probe safety (§4)**: never open env files, key stores, or credential-bearing config — existence only; missing tools log `BLOCKED`, never as project evidence.
- reference.md: extended WORKSPACE_MODEL / ASSUMPTION_REGISTER / CALIBRATION_LOG / BLIND_SPOT_REGISTER schemas (check_status, block/unblock reasons, corrected_belief, search_scope, premises, likelihood bands), worked scoped-null and BLOCKED log examples, blind-spot worked examples, pre-mortem and failure-mode worked examples, negative-search phrasing convention, fix-mode protocol, full worked report.

### Changed
- Phase 0 rewritten as 11 compact actions (scope recording, entry-point docs, system traces, hidden-state sweep, environment audit, test checklist, coverage ledger); enumerations moved to reference.md.
- Phase 2 classification eval-safe: `BLOCKED` is a `check_status` with `result: INCONCLUSIVE` (the result enum is untouched); FALSIFIED records keep the original prediction and add `corrected_belief`; untested assumptions still log (`SKIPPED` with a reason).
- Phase 2 example no longer cites a secret-bearing path as evidence.
- Depth-mode budgets made explicit (quick 10 / standard 25 / deep 50 by risk, + all load-bearing; overridable via `SELF_AUDIT_QUICK_TOP_N` / `SELF_AUDIT_MAX_ASSUMPTIONS`).
- SKILL.md frontmatter `version` → `1.2.0`; `run-self-audit.py --mode` default is now derived from `--stakes` when given (unchanged `deep` fallback), and the summary JSON reports the real mode/target/stakes (was hardcoded `quick`).

## [1.1.0] - 2026-10-22

### Added
- **User-context calibration**: in addition to model assumptions, the skill now surfaces what the user needs/intends/knows (even when unarticulated) and maps goal-task and tacit-knowledge gaps (USER_MISALIGNMENT / USER_GOAL_TASK_MISMATCH / USER_TACIT_GAP / USER_BLIND_SPOT categories). Enabled via the `--user-context` CLI flag (or `SELF_AUDIT_USER_CONTEXT=true`): Phase 0.5 discovers user-context signals from the workspace (stated docs claims, TODO debt, goal-vs-reality gaps) and Phase 1/2/3 test and classify them alongside model assumptions.
- **Self-learning loop**: assumptions already FALSIFIED in prior sessions are recorded as `KNOWN_FALSE` and skipped instead of re-tested.
- **Recurring error detection**: an assumption falsified 3+ times across sessions is escalated to `PERSISTENT_BLIND_SPOT` (Critical) with a recurring impact note.
- **Learning-unit lifecycle**: real `PENDING → VERIFIED → PERSISTED` state machine, kept in sync across the `learning-units/` artifact and the memory copy; orphaned `PENDING` units from prior runs are advanced.
- `.gitignore` for generated run artifacts and eval outputs.
- **HTML dashboard generator** (`generate-dashboard.py`): turns any audit's artifacts into a single self-contained `dashboard.html` — inline SVG charts (calibration curve with over/underconfidence divergence, blind-spot distribution, layer breakdown, outcome mix, trend), light/dark themes, data-table view, tooltips. No external libraries, works offline.

### Changed
- README rewritten with genuine run output, a why-stars section, and explicit harness-agnostic positioning (plain Python + Markdown/JSONL, no API key, static evals).
- Version aligned to `1.1.0` across `plugin.json` and `SKILL.md`.
- **SKILL.md trimmed** (884 → 787 lines): the four worked learning-unit examples were collapsed into one schema with per-category notes, with the full worked examples moved to `reference.md`. The epistemic-discipline rules, category tables, and phase contract stay in `SKILL.md` (the skill needs them to reason correctly). CONTRIBUTING's "under 500 lines" guidance was corrected — a hard `<500` target would force cutting substance the skill relies on.
- **Deterministic calibration tests**: the per-assumption simulation seed is now derived from SHA-256 of the assumption id (was Python's salted `hash()`), so results are reproducible across runs and machines.
- **All documented env vars are now real**: `SELF_AUDIT_MODE`, `SELF_AUDIT_VERBOSE`, `SELF_AUDIT_MAX_ASSUMPTIONS`, `SELF_AUDIT_QUICK_TOP_N`, `SELF_AUDIT_BLIND_SPOT_THRESHOLD`, `SELF_AUDIT_CROSS_MODEL_REVIEWERS`, and `SELF_AUDIT_TREND_MIN_SESSIONS` are wired into the pipeline (they were previously documented but unimplemented).
- **Deep-mode report metrics are computed, not fabricated**: the `Cross-Model Validation` and `Calibration Trend` sections of `calibration-report.md` now report real reviewer/agreement/trend stats instead of hardcoded placeholders.

### Fixed
- **Eval suite honesty**: eval graders now match the real artifact schema — accepts `KNOWN_FALSE` / `PERSISTENT_CALIBRATION_ERROR` log statuses and the `PERSISTENT_BLIND_SPOT` category, and no longer fails a run for having zero blind spots or zero falsified assumptions (a clean, well-calibrated workspace is a valid pass).
- **Eval wiring**: `case.yaml` declares `threshold` (was ignored) and `type: static` (was `llm`); `eval.yml` dispatch options match the runner's case names (also accepts the short `quick-mode` / `deep-mode` form).

## [1.0.0] - 2026-10-22

### Added
- Initial release of Self-Audit skill for Claude Code
- 6-phase epistemic calibration pipeline (Workspace Map → Assumption Extraction → Calibration Tests → Blind Spot Map → Learnable Units → Knowledge Base Update → Calibration Report)
- 3 depth modes: Quick (5-10 min), Standard (20-30 min), Deep (45-60+ min)
- Abstraction layer classification (L1 Syntax, L2 Pattern, L3 Architecture, L4 Domain)
- Epistemic status taxonomy (FACT, WORKSPACE_CONVENTION, ASSUMED_FACT, UNVERIFIED_PATTERN, IMPLICIT_CONVENTION, DOMAIN_GAP, CALIBRATION_ERROR, SPECULATION)
- Persistent calibration log (append-only JSONL) with confidence vs accuracy tracking
- Cross-model adversarial validation (Deep mode)
- Historical calibration trend analysis (Deep mode)
- Project memory system integration (`.claude/projects/<proj>/memory/`)
- CLI wrapper scripts: `run-self-audit.py`, `calibration-analytics.py`, `validate-assumptions.py`
- Output artifact templates: workspace-model, assumptions, blind-spots, learning-unit
- Eval cases for quick and deep modes with graders
- CI/CD workflows: validate, eval, release
- Comprehensive documentation: reference, examples, architecture, configuration, integration, troubleshooting
- Integration points with `using-agent-skills`, `doubt-driven-development`, `context-engineering`, `universal-brainstorming`, `spec-driven-development`, `code-review-and-quality`, `planning-and-task-breakdown`

### Security
- No known vulnerabilities at release

---

## [Unreleased]

### Planned
- Global knowledge sync mechanism (cross-project pattern sharing)
- Web dashboard for calibration visualization
- More language-specific convention detectors
- Automated memory pruning for stale entries
- Integration with `spec-driven-development` for assumption validation
- Support for `claude plugin eval` baseline comparison