# Self-Audit Skill — Reference Documentation

## Architecture Overview

The Self-Audit skill implements a 6-phase epistemic calibration pipeline:

```
┌─────────────────────────────────────────────────────────────────┐
│                    SELF-AUDIT PIPELINE                          │
├─────────────────────────────────────────────────────────────────┤
│                                                                 │
│  Phase 0: WORKSPACE MAP      →  WORKSPACE_MODEL.md/.json       │
│       │                                                              │
│       ▼                                                              │
│  Phase 1: ASSUMPTION EXTRACTION  →  ASSUMPTION_REGISTER.json     │
│       │                                                              │
│       ▼                                                              │
│  Phase 2: CALIBRATION TESTS    →  CALIBRATION_LOG.jsonl          │
│       │                                                              │
│       ▼                                                              │
│  Phase 3: BLIND SPOT MAP       →  BLIND_SPOT_REGISTER.md         │
│       │                                                              │
│       ▼                                                              │
│  Phase 4: LEARNABLE UNITS      →  LEARNING_UNITS/*.md            │
│       │                                                              │
│       ▼                                                              │
│  Phase 5: KNOWLEDGE BASE UPDATE  →  Memory files + Updated model │
│       │                                                              │
│       ▼                                                              │
│  Phase 6: CALIBRATION REPORT   →  CALIBRATION_REPORT.md + JSON   │
│                                                                 │
└─────────────────────────────────────────────────────────────────┘
```

## Data Schemas

### WORKSPACE_MODEL.json

```json
{
  "domain": "string",
  "target": "workspace|plan|diff|last-answer",
  "audit_purpose": "string (what the audit is for)",
  "decision_dependency": "string (which decision depends on the result)",
  "relevant_areas": ["string (paths in scope; everything else is a scope limit)"],
  "scope_limits": ["string (generated/, ignored/, unexamined areas — explicit)"],
  "repo_state": {"branch": "string", "clean": "boolean", "recent_log": ["string"]},
  "stack": {
    "languages": ["string"],
    "frameworks": ["string"],
    "build_tools": ["string"],
    "test_runners": ["string"],
    "linters": ["string"],
    "type_checkers": ["string"],
    "dependencies": {"package": "pinned version from manifest/lockfile"},
    "runtime_versions": {"python": "3.11 (from .python-version)"},
    "tools_available": {"tool": "boolean — missing tool = environment constraint"}
  },
  "structure": {
    "source_dirs": ["string"],
    "test_dirs": ["string"],
    "config_files": ["string"],
    "doc_dirs": ["string"],
    "memory_dirs": ["string"],
    "claude_files": ["string"],
    "entry_points": ["string (README, CLAUDE.md, AGENTS.md, Makefile, scripts, CI config, Dockerfile, .env.example)"]
  },
  "system_traces": {
    "entry_points": ["string"],
    "dependencies": ["module -> module"],
    "data_flow_paths": ["string"],
    "config_effects": ["string (which config key changes which behavior)"],
    "test_assertions": ["string (what behavior tests actually pin)"]
  },
  "tests": {
    "exist": "boolean",
    "run_command": "string",
    "pass_now": "boolean|null (null = not run)",
    "coverage_gaps": ["string"],
    "docs_claiming_untested_behavior": ["string"]
  },
  "environment": {
    "os": "string", "runtimes": ["string"], "network_constraints": ["string"],
    "required_services": ["string"], "required_secrets": ["existence only — never opened"]
  },
  "hidden_state": {
    "untracked_or_ignored": ["string"], "submodules": ["string"], "vendored": ["string"],
    "monorepo_workspaces": ["string"], "generated_looking_handwritten": ["string"]
  },
  "coverage_ledger": {
    "opened": ["path (read in full or relevant part)"],
    "seen_only": ["path (listed, grepped, or skimmed)"],
    "never_touched": ["path"],
    "commands_ran": ["string"],
    "commands_assumed": ["string (assumed to behave a certain way, never run)"]
  },
  "conventions": [
    {
      "pattern": "string",
      "frequency": "integer",
      "exceptions": ["string"],
      "status": "UNVERIFIED_PATTERN|WORKSPACE_CONVENTION|FACT",
      "evidence_files": ["string"]
    }
  ],
  "memory_index": [
    {
      "name": "string",
      "description": "string",
      "layer": "L1|L2|L3|L4",
      "verified": "boolean",
      "calibration_delta": "number"
    }
  ],
  "calibration_history": [
    {
      "session_id": "string",
      "timestamp": "ISO8601",
      "mode": "quick|standard|deep",
      "total_assumptions": "integer",
      "falsified_count": "integer",
      "mean_delta": "number"
    }
  ],
  "open_questions": ["string"]
}
```

### ASSUMPTION_REGISTER.json

```json
[
  {
    "id": "ASSUME-001",
    "type": "CONVENTION|BEHAVIORAL|INVARIANT|DELEGATION|ARCHITECTURAL|DOMAIN|USER_INTENT|USER_NEED|USER_TACIT|USER_BLIND",
    "claim_kind": "architecture|build_run|module_behavior|test_coverage|dependency_api|domain_rule|user_model",
    "statement": "string",
    "source_evidence": "string",
    "provenance": "OBSERVED_THIS_SESSION|INFERRED|RECALLED|ASSUMED",
    "verified_this_session": "boolean (false for anything loaded from memory/prior logs)",
    "reasoning_chain": ["string (required when provenance=INFERRED)"],
    "confidence": 0.85,
    "likelihood_band": "HIGH|MEDIUM|LOW (for claims without calibration-log entries — §2)",
    "testable": true,
    "layer": "L1|L2|L3|L4",
    "scope": "workspace|universal",
    "falsifier": "string",
    "preconditions": ["string (what must be true for the claim to hold)"],
    "edge_cases_unexamined": ["string"],
    "possible_confusions": ["string (similar names/configs/paths that could mean something else)"],
    "load_bearing": "boolean",
    "impact": "3|2|1 (decision-blocking|significant|minor)",
    "epistemic_status": "ASSUMED_FACT|UNVERIFIED_PATTERN|USER_INFERRED"
  }
]
```

### CALIBRATION_LOG.jsonl (one record per line)

```json
{
  "assumption_id": "ASSUME-001",
  "session_id": "uuid",
  "timestamp": "2026-10-22T10:30:00Z",
  "prediction": "string",
  "actual": "string",
  "evidence": ["string"],
  "result": "CONFIRMED|FALSIFIED|INCONCLUSIVE|USER_CONFIRMED",
  "check_status": "RAN|BLOCKED|SKIPPED",
  "block_reason": "string (check_status=BLOCKED only)",
  "unblock_condition": "string (check_status=BLOCKED only)",
  "inconclusive_reason": "string (result=INCONCLUSIVE only)",
  "confidence_delta": -0.12,
  "corrected_belief": "string (result=FALSIFIED only — what the truth is; original prediction is retained)",
  "new_status": "FACT|WORKSPACE_CONVENTION|CALIBRATION_ERROR|UNVERIFIED_PATTERN",
  "layer": "L2",
  "verification_method": "code_execution|static_analysis|doc_test_crossref|memory_crosscheck|expert_query",
  "search_scope": {"paths": ["string"], "ignore_rules": "string", "case_sensitive": "boolean", "file_types": ["string"]},
  "commands_ran": ["string"],
  "commands_assumed": ["string"]
}
```

**Worked example — scoped-null CONFIRMED (null-cap applied, §4):**
```jsonl
{"assumption_id": "ASSUME-031", "session_id": "uuid", "timestamp": "2026-10-22T10:40:00Z", "prediction": "No raw SQL in core module", "actual": "no matches", "evidence": ["rg 'SELECT |INSERT |UPDATE |DELETE ' core/ -> 0 matches"], "result": "CONFIRMED", "check_status": "RAN", "verification_method": "static_analysis", "search_scope": {"paths": ["core/"], "ignore_rules": "default", "case_sensitive": false, "file_types": [".py"]}, "commands_ran": ["rg -i 'select |insert |update |delete ' core/"], "commands_assumed": [], "confidence_delta": 0.15, "new_status": "WORKSPACE_CONVENTION", "claim_wording": "no counterexamples in core/ (*.py, case-insensitive)", "layer": "L3", "assumption_origin": "model"}
```
Note: a counterexample *search* never yields automatic FACT at 1.0 — the claim is worded "no counterexamples in <scope>" and capped at `WORKSPACE_CONVENTION`.

**Worked example — BLOCKED check (result stays INCONCLUSIVE):**
```jsonl
{"assumption_id": "ASSUME-052", "session_id": "uuid", "timestamp": "2026-10-22T10:45:00Z", "prediction": "Full test suite passes on this commit", "actual": "test run not executed", "evidence": [], "result": "INCONCLUSIVE", "check_status": "BLOCKED", "block_reason": "pytest not installed in this environment", "unblock_condition": "install dev deps (pip install -e .[dev]) or run in CI", "inconclusive_reason": "check could not run; no project evidence gathered", "confidence_delta": 0.0, "new_status": "UNVERIFIED_PATTERN", "layer": "L2", "verification_method": "code_execution", "search_scope": null, "commands_ran": [], "commands_assumed": ["python -m pytest (never invoked)"]}
```
Note: `BLOCKED` is a **check status**, never a result value — the result enum is unchanged.

### BLIND_SPOT_REGISTER.md (also machine-readable JSON)

```json
[
  {
    "id": "BS-001",
    "category": "CALIBRATION_ERROR|UNVERIFIED_CRITICAL|IMPLICIT_CONVENTION_GAP|DOMAIN_GAP|MEMORY_DRIFT|POSSIBLE_BLIND_SPOT|USER_MISALIGNMENT|USER_TACIT_GAP|USER_BLIND_SPOT|USER_GOAL_TASK_MISMATCH|USER_IMPLICIT_CONSTRAINT_VIOLATION|USER_UNSTATED_REQUIREMENT",
    "layer": "L1|L2|L3|L4",
    "severity": "Critical|High|Medium|Low",
    "assumption_id": "ASSUME-001",
    "assumption_statement": "string",
    "premises": ["string (what must be true for the claim to hold)"],
    "evidence_summary": "string",
    "confidence_delta": -0.72,
    "likelihood_band": "HIGH|MEDIUM|LOW (unmeasured claims — §2 measurement split)",
    "unexamined_paths": ["string (edge cases / paths never touched)"],
    "discoverability": "Easy|Moderate|Hard",
    "impact": "string",
    "smallest_useful_check": "string (the single cheapest probe that could settle it)",
    "learning_objective": "string",
    "verification_protocol": "string",
    "integration_points": ["string"],
    "learning_unit_id": "LU-001",
    "status": "NEW|IN_PROGRESS|LEARNING_UNIT_CREATED|VERIFIED|PERSISTED"
  }
]
```

**Note on `smallest_useful_check`:** one probe per blind spot, chosen by the §4 cheapest-decisive rule — the register entry is a pointer to the next action, not a research plan. Numeric `confidence_delta` appears only for calibration-logged claims; everything else carries `likelihood_band`.

### Blind-Spot Worked Examples (user categories)

```markdown
### BLIND_SPOT-012 (User: USER_MISALIGNMENT)
- **Category**: USER_MISALIGNMENT
- **Layer**: L3 (Architecture) · **Severity**: Critical
- **Claim**: "User intends clean architecture (stated: 'we follow clean architecture')"
- **Premises**: user statement reflects current mental model; workspace layout is representative
- **Evidence**: Import graph shows core imports runtime/ and system/ directly; modular monolith, no layer separation
- **Confidence Delta**: -0.80 (user confidence 0.9, workspace evidence 0.1)
- **Unexamined Paths**: other monorepo packages that might enforce layers
- **Discoverability**: Moderate (requires user statement + workspace analysis) · **Impact**: user will make architecture decisions assuming clean layers; actual code violates this
- **Smallest Useful Check**: show the user the import graph and ask one confirm/refine question
- **Learning Objective**: Align user mental model with actual architecture
- **Verification Protocol**: Present import graph to user; confirm/refine mental model
- **Integration Point**: `using-agent-skills` pre-check — flag before architecture tasks
```

```markdown
### BLIND_SPOT-019 (User: USER_TACIT_GAP)
- **Category**: USER_TACIT_GAP
- **Layer**: L4 (Domain) · **Severity**: High
- **Claim**: "All monetary values use cents (integers)" (tacit)
- **Premises**: legacy billing/ is still active code, not dead
- **Evidence**: 95% use Money type (cents), 5% use float for prices in legacy billing/
- **Confidence Delta**: -0.65 (tacit confidence 0.95, workspace evidence 0.3 for legacy)
- **Unexamined Paths**: report generators importing billing floats
- **Discoverability**: Hard (requires cross-module type analysis) · **Impact**: legacy billing calculates in floats → rounding errors in financial reports
- **Smallest Useful Check**: `rg 'float' billing/` and open the top hit
- **Learning Objective**: Document Money type as required pattern; migrate legacy billing
- **Verification Protocol**: Type-check all price calculations; flag float usage
- **Integration Point**: `code-review-and-quality` — flag float price calculations
```

```markdown
### BLIND_SPOT-027 (User: USER_GOAL_TASK_MISMATCH)
- **Category**: USER_GOAL_TASK_MISMATCH
- **Layer**: L3 (Architecture) · **Severity**: Critical
- **Claim**: "Quick refactor of auth module (2 days)" (user stated goal)
- **Premises**: the 2-day estimate assumes the current test/dependency state is benign
- **Evidence**: Auth has 50% test coverage, circular deps with 3 services, no interfaces
- **Confidence Delta**: N/A (goal vs. reality mismatch) — **Likelihood**: HIGH
- **Unexamined Paths**: downstream consumers of auth outside the three known services
- **Discoverability**: Easy (code analysis + user statement) · **Impact**: 2-day estimate → 3-week stabilization; user will be blocked
- **Smallest Useful Check**: run dependency analysis + coverage on auth module only
- **Learning Objective**: Calibrate effort estimates to workspace reality
- **Verification Protocol**: Run dependency analysis + test coverage on auth module
- **Integration Point**: `planning-and-task-breakdown` — weight risk by blind spot severity
```

### LEARNING_UNIT.md (per unit)

```markdown
# LEARNING_UNIT-<NNN>

## Metadata
- **id**: LU-<NNN>
- **blind_spot_id**: BS-<NNN>
- **layer**: L<1-4>
- **status**: PENDING|IN_PROGRESS|VERIFIED|PERSISTED
- **created_session**: <session-id>
- **verified_session": <session-id>

## Learning Objective
<string>

## Current Belief (Falsified)
<string> — CALIBRATION_ERROR, delta <number>

## Corrected Understanding
<string>

## Verification Protocol
1. <step 1>
2. <step 2>
...

## Success Criteria
- <criterion 1>
- <criterion 2>
...

## Knowledge Artifact
- **Type**: ADR|Pattern Doc|Test Case|Docstring|Config Example
- **Location**: `${KNOWLEDGE_ROOT}/learning-units/<id>.md`
- **Memory Pointer**: `${MEMORY_ROOT}/<slug>.md`
- **Integration Points**: ["skill1", "skill2"]

## Evidence
- <evidence 1>
- <evidence 2>
...

## Falsifier
<string> — condition that would invalidate this learning
```

### Worked Examples (one per category)

These complete, real-shaped learning units show how the schema adapts per blind-spot category. The model variants cite the model's assumption; the user variants cite the user's stated goal, mental model, or tacit assumption.

#### Model: CALIBRATION_ERROR (LU-007)

```markdown
# LEARNING_UNIT-007 (Model: CALIBRATION_ERROR)
## Learning Objective
Understand workspace's actual module architecture and dependency rules.

## Current Belief (Falsified)
Clean architecture layers (domain/app/infra) — CALIBRATION_ERROR, delta -0.72

## Corrected Understanding
Modular monolith with core as central domain module; runtime/ is operational scripts; system/ is infrastructure. No strict layer enforcement.

## Verification Protocol
1. Generate full import graph: `pydeps core --show-deps -T svg`
2. Document module categories: domain, operational, infrastructure, test
3. Check for circular dependencies
4. Compare with any ADR/architecture doc

## Success Criteria
- Import graph generated and analyzed
- Module taxonomy documented with evidence
- Any circular deps flagged
- Architecture pattern named and described

## Knowledge Artifact Template
- **Type**: Architecture Decision Record (ADR) or Pattern Doc
- **Location**: `.claude/knowledge/learning-units/architecture-pattern.md`
- **Memory Pointer**: Add to `.claude/projects/<proj>/memory/MEMORY.md`
- **Integration**: Tag for `doubt-driven-development` pre-check, `context-engineering` load

## Status
PENDING → IN_PROGRESS → VERIFIED → PERSISTED
```

#### User: USER_MISALIGNMENT (LU-012)

```markdown
# LEARNING_UNIT-012 (User: USER_MISALIGNMENT)
## Learning Objective
Align user mental model with actual workspace architecture.

## Current Belief (Falsified)
User believes: "We follow clean architecture" — USER_MISALIGNMENT, delta -0.80

## Corrected Understanding
User's mental model is clean architecture; actual is modular monolith. Gap causes wrong architectural decisions.

## Verification Protocol
1. Present import graph showing cross-layer imports
2. Ask user to describe their mental model
3. Co-create accurate architecture documentation
4. Update ADR-001 or create new ADR

## Success Criteria
- User acknowledges modular monolith pattern
- Architecture doc updated to reflect reality
- Future decisions use correct model

## Knowledge Artifact Template
- **Type**: User Mental Model Alignment Doc
- **Location**: `.claude/knowledge/learning-units/user-architecture-model.md`
- **Memory Pointer**: Add to `.claude/projects/<proj>/memory/user-architecture-model.md`
- **Integration**: Tag for `using-agent-skills` pre-check, `planning-and-task-breakdown`

## Status
PENDING → IN_PROGRESS → VERIFIED → PERSISTED
```

#### User: USER_TACIT_GAP (LU-019)

```markdown
# LEARNING_UNIT-019 (User: USER_TACIT_GAP)
## Learning Objective
Enforce Money type for all monetary values; eliminate float price calculations.

## Current Belief (Falsified)
User tacitly assumes all prices in cents — USER_TACIT_GAP, delta -0.65

## Corrected Understanding
95% of codebase correctly uses Money type (cents), but legacy billing/ uses float → financial rounding errors.

## Verification Protocol
1. Type-check all price calculations across workspace
2. Identify all float price usages in billing/
3. Create migration plan for legacy billing to Money type
4. Add linting rule: "no float for monetary values"

## Success Criteria
- Zero float price calculations in workspace
- Linting rule enforced in CI
- Legacy billing migrated to Money type

## Knowledge Artifact Template
- **Type**: Domain Convention + Linting Rule
- **Location**: `.claude/knowledge/learning-units/money-type-enforcement.md`
- **Memory Pointer**: Add to `.claude/projects/<proj>/memory/money-type-enforcement.md`
- **Integration**: Tag for `code-review-and-quality`, `context-engineering`

## Status
PENDING → IN_PROGRESS → VERIFIED → PERSISTED
```

#### User: USER_GOAL_TASK_MISMATCH (LU-027)

```markdown
# LEARNING_UNIT-027 (User: USER_GOAL_TASK_MISMATCH)
## Learning Objective
Calibrate effort estimates to workspace reality for auth module.

## Current Belief (Falsified)
User estimates: "Quick auth refactor (2 days)" — USER_GOAL_TASK_MISMATCH, Critical

## Corrected Understanding
Auth module requires 3-week stabilization: 50% test coverage, 3 circular deps, no interfaces. Quick refactor impossible.

## Verification Protocol
1. Run full dependency analysis on auth module
2. Measure test coverage per file
3. Identify circular dependency chains
4. Create phased refactor plan with milestones

## Success Criteria
- Realistic effort estimate documented (3 weeks)
- Phased plan with measurable milestones
- User acknowledges revised timeline

## Knowledge Artifact Template
- **Type**: Effort Calibration Doc
- **Location**: `.claude/knowledge/learning-units/auth-refactor-effort.md`
- **Memory Pointer**: Add to `.claude/projects/<proj>/memory/auth-refactor-effort.md`
- **Integration**: Tag for `planning-and-task-breakdown`, `using-agent-skills` pre-check

## Status
PENDING → IN_PROGRESS → VERIFIED → PERSISTED
```

## Worked Example — CALIBRATION_REPORT.md (v1.2 display order)

```markdown
# SELF-AUDIT REPORT — my-project — 2026-10-23

## Bottom Line
My picture of this workspace is reliable on structure and error handling, shaky on how tests
are actually run. The single biggest gap: I have never executed the test suite, so every
"tests pass" belief is unverified.

## Corrected Beliefs
- "All config files use YAML" → false: YAML at repo root, JSON under runtime/ (evidence: `runtime/config.json`, `runtime/defaults.json`).
- "Clean architecture layers" → false: modular monolith; `core/` imports `runtime/` directly.

## Claims Table
| Claim | Tier | Provenance | Confidence | Evidence or check performed |
|-------|------|------------|------------|-----------------------------|
| Handlers use `Result<T,E>` | WORKSPACE_CONVENTION | OBSERVED_THIS_SESSION | High (0.9) | `rg 'Result<' src/` — 30/35 files |
| pytest runs the suite | ASSUMED_FACT | RECALLED | Low (0.3) | none — never executed |
| Prices in cents | ASSUMED_FACT | INFERRED | Medium | `rg 'float' billing/` — 5 hits (partial) |
| (+14 further claims) | ... | ... | ... | summarized in CALIBRATION_LOG |

## Top Blind Spots (by risk)
| Rank | ID | Category | Layer | Severity | LU |
|------|-----|----------|-------|----------|----|
| 1 | BS-003 | CALIBRATION_ERROR | L3 | Critical | LU-007 ✓ |
| 2 | BS-027 | USER_GOAL_TASK_MISMATCH | L3 | Critical | LU-027 ✓ |

## Coverage Gaps & Scope Limits
- Never touched: `services/legacy/`, `deploy/` (top of Blind Area Ranking)
- Scope limit: generated code under `build/` excluded per Phase 0
- Negative-search scopes relied on: "no raw SQL in core/" — scope `core/` `*.py` only

## Still Unverified
- ASSUME-052 "test suite passes" — BLOCKED (pytest not installed); unblock: `pip install -e .[dev]`, then `python -m pytest`
- ASSUME-061..063 — untested (budget: standard top-25 cut them)

## Open Questions
- What deploy target does `deploy/terraform/` assume? (cannot be settled from the workspace alone; changes the release plan)

## Epistemic Buckets
| Established | Uncertain | Not-Yet-Examined | Recommended Probes |
|-------------|-----------|------------------|--------------------|
| Result<T,E> convention; JSON/YAML split | prices-in-cents enforcement | services/legacy/ | `pip install -e .[dev] && python -m pytest` |
| modular monolith imports | auth coverage claim | deploy/ | `rg 'float' billing/` (finish) |

## Stop Reason
**STOP G+H**: every load-bearing claim verified or labeled; remaining checks cost more
than the refactor decision is worth. Cost of stopping: the "tests pass" belief stays
unverified — first action next session is the blocked pytest run.

---
## Appendix
(session meta, assumption statistics, calibration curve, user context alignment,
learning units, cross-model validation, trend analysis, pre-load recommendations)
```

## Configuration

### Environment Variables

| Variable | Default | Description |
|----------|---------|-------------|
| `SELF_AUDIT_MODE` | `deep` | Default depth mode: `quick`, `standard`, `deep` |
| `SELF_AUDIT_WORKSPACE` | `${CLAUDE_PROJECT_DIR}` | Workspace root to audit |
| `SELF_AUDIT_KNOWLEDGE_ROOT` | `${CLAUDE_PROJECT_DIR}/.claude/knowledge/` | Output directory for artifacts |
| `SELF_AUDIT_MEMORY_ROOT` | `${CLAUDE_PROJECT_DIR}/.claude/projects/<slug>/memory/` | Memory system root |
| `SELF_AUDIT_CROSS_MODEL` | `true` | Enable cross-model validation (deep mode) |
| `SELF_AUDIT_TREND_ANALYSIS` | `true` | Enable historical trend analysis (deep mode) |
| `SELF_AUDIT_MAX_ASSUMPTIONS` | `100` | Max assumptions to extract (deep mode) |
| `SELF_AUDIT_QUICK_TOP_N` | `20` | Top N assumptions for quick mode |
| `SELF_AUDIT_BLIND_SPOT_THRESHOLD` | `0.5` | Min |confidence_delta| to register as blind spot |
| `SELF_AUDIT_VERBOSE` | `false` | Verbose logging |

### Skill Arguments (from frontmatter `arguments`)

| Argument | Type | Description |
|----------|------|-------------|
| `mode` | `quick|standard|deep` | Override depth mode |
| `workspace` | `string` | Override workspace path |
| `target` | `workspace\|plan\|diff\|last-answer` | What is being audited (§7; default `workspace`) |
| `stakes` | `low\|medium\|high` | Verification budget (§7; default `medium`; sets default mode) |
| `output-dir` | `string` | Override knowledge root |
| `user-context` | flag | Enable Phase 0.5 user context discovery explicitly |

### Example Invocations

```bash
# Quick mode on current project
/self-audit --mode quick

# High-stakes audit of a plan (mode defaults to deep from stakes)
/self-audit --target plan --stakes high "plan text or path"

# Diff audit before release
/self-audit --target diff --stakes high

# Deep mode on specific workspace
/self-audit --mode deep --workspace /path/to/project

# Custom output directory
/self-audit --mode standard --output-dir /custom/knowledge/path

# With environment variables
SELF_AUDIT_MODE=quick SELF_AUDIT_VERBOSE=true /self-audit
```

## Integration Points

### using-agent-skills Pre-Check Hook

Add to `using-agent-skills` skill or as a standalone hook:

```bash
# In using-agent-skills discovery flow, before major task:
/self-audit --mode quick
# Load CALIBRATION_SUMMARY.json + top 3 learning units
```

### doubt-driven-development Doubt Seeds

```bash
# Feed L3/L4 blind spots as adversarial review targets
# BLIND_SPOT_REGISTER.md → filter layer >= L3 → doubt-driven-development
```

### context-engineering Context Load

```bash
# Primary context files to load:
# 1. WORKSPACE_MODEL.md
# 2. High-priority LEARNING_UNITS (VERIFIED, layer >= L2)
# 3. CALIBRATION_SUMMARY.json (for calibration awareness)
```

### spec-driven-development Assumption Validation

```bash
# Cross-reference spec assumptions against CALIBRATION_LOG
# Any spec assumption matching a CALIBRATION_ERROR → flag for review
```

## Pre-Mortem Protocol (all modes)

The pre-mortem runs in **every** mode — it is the cheapest defense against "this all looks fine." Full procedure (SKILL.md, Pre-Mortem Protocol):

1. Ask: "If a maintainer who knows this repo well reviewed my conclusions, what **three** things would they say I got wrong or missed?" Exactly three items.
2. For each item: register the claim (ordering invariant), then run **one decisive check** aimed at it.
3. Fold results into the register and blind-spot map; update the picture immediately.
4. **Deep extension:** hand the three items to a fresh-context cross-model reviewer to attack; disagreements log as `CONTRADICTION` (Anti-Pattern #10).

**Worked example (short form):**
1. *"They'd say I assumed the test suite runs green."* → check: run the suite (or `check_status: BLOCKED` + `unblock_condition: install dev deps`).
2. *"They'd say I mistook generated code for hand-written."* → check: open the suspicious file's header/comment block.
3. *"They'd say my 'convention' is just the two files I happened to read."* → check: scoped count across the claimed scope (`rg ... | wc -l` with `search_scope` recorded).

The three checks count toward the Phase 2 budget; padding past three is filler (Anti-Pattern #14).

## Failure-Mode Scan — Worked Examples

Each scan item (SKILL.md, Phase 3) with what catching it looks like:

| # | Failure mode | Caught when |
|---|--------------|-------------|
| 1 | Filename-implies-content | `runtime/config.json` believed to hold active config because of its name; opening it shows an example template |
| 2 | Sample → whole | "All handlers use `Result`" from 3 sampled files; scoped count shows 30 of 35 |
| 3 | Prose over behavior | README says `make test` runs the suite; the Makefile target runs only lint (→ `finding_kind: DOC_DRIFT`) |
| 4 | Assumed command/flag | `pytest --lf` assumed to exist under the pinned pytest 5.x (it doesn't) |
| 5 | Assumed green | "Tests pass" read off a CI badge; never run this session |
| 6 | Not-found = doesn't-exist | "No auth module" after grepping `auth` under `src/` only — the module lives in `services/` |
| 7 | Stale restatement | Phase 6 report re-cites the pre-Phase-2 architecture claim after a check already corrected it |

## Cross-Model Validation (Deep Mode)

### Reviewer Invocation

```bash
# Spawn fresh-context reviewer agents
# Each reviewer gets: BLIND_SPOT_REGISTER + relevant assumptions + workspace model
# Reviewer prompt: "Adversarially verify these calibration findings. Find errors, confirm falsifications, identify additional blind spots."
```

### Validation Log Schema (CROSS_MODEL_VALIDATION.log.jsonl)

```json
{
  "blind_spot_id": "BS-003",
  "reviewer": "reviewer-1",
  "model": "claude-opus-5",
  "verdict": "CONFIRMED|REFUTED|PARTIAL|ADDITIONAL_FINDING",
  "notes": "string",
  "additional_blind_spots": ["BS-new-001", "BS-new-002"],
  "timestamp": "ISO8601"
}
```

### Consensus Rules

- **Confirmed**: ≥2 reviewers agree on falsification
- **Refuted**: ≥2 reviewers find assumption was actually correct
- **Partial**: Mixed verdicts — log as `CONTRADICTION`, flag for human review
- **Additional**: New blind spots discovered by reviewers → add to register

## Historical Trend Analysis (Deep Mode)

### Input

- `CALIBRATION_LOG.jsonl` (all sessions)
- `BLIND_SPOT_REGISTER.md` history (if persisted)

### Metrics Computed

| Metric | Formula | Interpretation |
|--------|---------|----------------|
| Mean |δ| | Σ\|confidence_delta\| / N | Overall calibration error |
| Overconfidence rate | Count(δ < -0.3) / N | Systematic overconfidence |
| Underconfidence rate | Count(δ > 0.3) / N | Systematic underconfidence |
| Layer-specific drift | Mean |δ| per layer | Where model struggles |
| Recurring blind spots | Count same category across sessions | Persistent gaps |
| Calibration improvement | Mean |δ| session N vs N-3 | Trend direction |

### Trend Report Output (CALIBRATION_TREND_REPORT.md)

```markdown
# CALIBRATION TREND REPORT — 2026-10-22

## Sessions Analyzed: 12

## Overall Calibration
- Mean |delta|: 0.18 (was 0.31 at session 1) → **IMPROVING**
- Overconfidence rate: 23% (was 45%)
- Underconfidence rate: 8% (was 12%)

## By Layer
| Layer | Mean |δ| | Trend | Recurring Issues |
|-------|------|-------|------------------|
| L1 | 0.05 | Stable | None |
| L2 | 0.22 | Improving | Config conventions (8/12 sessions) |
| L3 | 0.31 | Stable | Architecture assumptions (6/12) |
| L4 | 0.15 | Improving | Domain knowledge (first capture session 10) |

## Persistent Weak Spots
1. **L2 Config Conventions** — Recurring in 8/12 sessions. Model assumes YAML; workspace uses JSON+YAML mix.
2. **L3 Architecture Assumptions** — Clean architecture assumed; actual patterns vary (modular monolith, layered, hexagonal).

## New Improvements
- **L4 Domain Knowledge** — First structured capture in session 10. Now tracked.

## Recommendations
- Add config convention to memory (WORKSPACE_CONVENTION)
- Document actual architecture pattern in ADR
- Continue L4 domain knowledge capture
```

## Verification Methods Reference

**Choosing a check (§4):** run the **cheapest decisive check** — the one defined by the claim's `falsifier`, capable of returning FALSIFIED. Confirm-only probes (re-reading your own reasoning or the doc the belief came from) are not verification. Prefer disconfirmation: pick the check most likely to prove the picture wrong. Every search-based recipe below must record its `search_scope` (`paths`, `ignore_rules`, `case_sensitive`, `file_types`) or run as `INCONCLUSIVE` / `check_status: BLOCKED`.

**Tooling note:** a missing tool (no `rg`, no `mypy`, no network) is an **environment constraint** — log `check_status: BLOCKED` with `block_reason` and `unblock_condition`, never as project evidence. Scripts and one-off commands run with the same probe-safety rules (§4): no destructive actions, no state mutation, never open env files or key stores.

### 1. Code Execution
```bash
# Run test
python -m pytest tests/ -xvs -k "test_name" 2>&1

# Run script
python script.py --arg value 2>&1

# Type check
mypy module.py 2>&1
```

### 2. Static Analysis (grep/rg)
```bash
# Pattern search
rg "pattern" --type py --glob "!test_*" .

# Count occurrences
rg "pattern" --type py . | wc -l

# Find counterexamples
rg "anti-pattern" --type py .
```

### 3. Document Cross-Reference
```bash
# Compare docstring vs implementation
# Extract docstring
grep -A 20 "def function_name" module.py | head -30

# Compare with README/ADR
grep -r "convention" docs/ README.md ADR/
```

### 4. Memory/ADR Consistency
```bash
# Check memory files
cat .claude/projects/*/memory/*.md | grep -i "pattern"

# Check ADRs
cat docs/adr/*.md | grep -i "decision"
```

### 5. Import Graph Analysis
```bash
# Python
pydeps module --show-deps -T svg > import-graph.svg

# JavaScript/TypeScript
madge --image graph.png src/

# General
grep -r "import " --include="*.py" . | sort | uniq -c | sort -rn
```

### 6. Recalled Version Cross-Check
```bash
# Compare what memory "remembers" against the pinned reality
python -c "import json;d=json.load(open('package.json'));print(d.get('dependencies',{}))"
grep -E "^(requests|pytest)" requirements.txt pyproject.toml 2>/dev/null
python -c "import requests; print(requests.__version__)"
```
Memory is the unreliable side of this comparison (§4 version suspicion). A mismatch is a `CALIBRATION_ERROR` in the making; only the pinned manifest/lockfile match earns FACT. Any version-like name or fast-moving library is suspect until checked this way.

### 7. Flag/API Existence
```bash
# Confirm a command, flag, or API exists in the pinned version BEFORE relying on it
tool --help | grep -- "--flag"
python -c "import lib; print(hasattr(lib, 'api_name'))"
# Dry run where available
tool --flag --dry-run
```
Failure of an unconfirmed invocation is never project evidence — confirm existence first, then run (§4). If the workspace ships its own probe scripts under `scripts/`, they may be run read-only; a script that cannot run is `check_status: BLOCKED` (environment constraint), not a finding.

## Negative-Search Scope Convention

A null result is evidence only inside a stated scope (§4). Record `search_scope` with every search-based check.

**Approved phrasing:**
- "No counterexamples in `core/` (`*.py`, case-insensitive, default ignores)"
- "Not found under scope S: paths `[...]`, file_types `[...]`"
- "0 matches across 12 files searched (command output attached)"

**Forbidden phrasing:**
- "X does not exist" / "there are no X" (unscoped)
- "Everything passes" (without naming what ran and over what)
- "Clean" / "No issues" (no scope, no command)
- "All configs are YAML" from a search that only globbed `*.yaml`

A search whose scope cannot be stated up front runs as `INCONCLUSIVE` / `check_status: BLOCKED`. A null counterexample search with a complete bounded scope yields `CONFIRMED` worded "no counterexamples in <scope>", capped at `WORKSPACE_CONVENTION` — never automatic FACT at 1.0.

## Fix Mode Protocol

**Trigger:** explicit user request only ("fix it", "apply the fixes", "open fix mode") — never inferred from how severe the findings are (Anti-Pattern #12). The audit report always ships first; fixes are a separate, approved step.

1. **Concrete proposals** — one per finding: the exact edit/test/doc change, the finding it fixes, and the check that will confirm it.
2. **Approval gate** — apply only on explicit user approval, change by change; partial approval is normal and honored.
3. **Apply** — knowledge/memory writes (Zone A) are pre-authorized; any audited-workspace edit is authorized only for the approved change.
4. **Post-fix re-verification** — re-run the finding's decisive check and log it in `CALIBRATION_LOG.jsonl`; a fix that isn't re-verified is a new assumption.
5. **Staleness note** — fixes create new state: if they touched load-bearing claims, mark the workspace model stale in the report.

## Error Handling

| Error | Handling |
|-------|----------|
| Workspace not found | Exit with clear error; suggest `--workspace` |
| No write permission to `.claude/` | Exit; instruct user to grant permission |
| Calibration log corrupted | Backup, start fresh; log warning |
| Cross-model reviewer fails | Log failure, continue with remaining reviewers |
| Memory system unavailable | Write to knowledge root only; warn |
| Phase timeout | Save progress, continue from next phase |

## Performance Targets

| Mode | Max Duration | Max Assumptions | Max Blind Spots |
|------|--------------|-----------------|-----------------|
| Quick | 10 min | 20 | 5 |
| Standard | 30 min | 50 | 15 |
| Deep | 60 min | 100 | 30 |

## Version History

| Version | Date | Changes |
|---------|------|---------|
| 1.2.0 | 2026-10-23 | Superset rigor: provenance + evidence cutoff, search_scope/negative-search discipline, measurement split, pre-mortem in all modes, coverage ledger, fix mode & write policy, stakes/target scope, redesigned report, Anti-Patterns #11–#20 |
| 1.1.0 | 2026-10-22 | User-context calibration (USER_* categories), self-learning loop (KNOWN_FALSE), recurring-error detection, LU lifecycle, HTML dashboard |
| 1.0.0 | 2026-10-22 | Initial release: 6-phase pipeline, 3 depth modes, cross-model validation, trend analysis, memory integration |

## Related Skills

| Skill | Relationship |
|-------|--------------|
| `using-agent-skills` | Pre-check consumer |
| `doubt-driven-development` | Blind spot consumer |
| `context-engineering` | Context provider |
| `universal-brainstorming` | Seed provider |
| `spec-driven-development` | Assumption validator |
| `code-review-and-quality` | Calibration checker |
| `planning-and-task-breakdown` | Risk input provider |