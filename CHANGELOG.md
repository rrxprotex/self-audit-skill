# Changelog

All notable changes to this project will be documented in this file.

The format is based on [Keep a Changelog](https://keepachangelog.com/en/1.0.0/),
and this project adheres to [Semantic Versioning](https://semver.org/spec/v2.0.0.html).

## [1.1.0] - 2026-10-22

### Added
- **User-context calibration**: in addition to model assumptions, the skill now surfaces what the user needs/intends/knows (even when unarticulated) and maps goal-task and tacit-knowledge gaps (`--user-context`, USER_MISALIGNMENT / USER_GOAL_TASK_MISMATCH / USER_TACIT_GAP categories).
- **Self-learning loop**: assumptions already FALSIFIED in prior sessions are recorded as `KNOWN_FALSE` and skipped instead of re-tested.
- **Recurring error detection**: an assumption falsified 3+ times across sessions is escalated to `PERSISTENT_BLIND_SPOT` (Critical) with a recurring impact note.
- **Learning-unit lifecycle**: real `PENDING → VERIFIED → PERSISTED` state machine, kept in sync across the `learning-units/` artifact and the memory copy; orphaned `PENDING` units from prior runs are advanced.
- `.gitignore` for generated run artifacts and eval outputs.

### Changed
- README rewritten with genuine run output, a why-stars section, and explicit harness-agnostic positioning (plain Python + Markdown/JSONL, no API key, static evals).
- Version aligned to `1.1.0` across `plugin.json` and `SKILL.md`.

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