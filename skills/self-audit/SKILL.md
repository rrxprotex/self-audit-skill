---
name: self-audit
description: Discovers what the model doesn't know it doesn't know in the workspace. Runs structured epistemic calibration: scans for implicit assumptions, tests them against evidence, maps blind spots by abstraction layer (L1-L4), synthesizes learnable units with verification protocols, persists calibrated knowledge to project memory. Use at session start, before major tasks, when confidence feels uncalibrated, or to convert workspace patterns into durable knowledge artifacts. Deep mode (default) includes cross-model adversarial validation and historical calibration trend analysis.
when_to_use: "Starting a new session in a workspace; before major implementation tasks; when repeatedly surprised by same workspace patterns; when cross-session learning keeps resetting; when you need to audit your own knowledge boundaries before claiming expertise"
argument-hint: "[--mode quick|standard|deep] [--workspace PATH] [--output-dir PATH]"
arguments: "mode workspace output-dir"
disable-model-invocation: false
user-invocable: true
allowed-tools: "Bash(${CLAUDE_SKILL_DIR}/scripts/run-self-audit.py *) Glob Grep Read Write Edit Task Agent"
model: inherit
effort: high
context: fork
agent: general-purpose
background: true
shell: bash
metadata:
  category: "meta-learning"
  tags: ["epistemic-calibration", "workspace-analysis", "knowledge-discovery", "blind-spot-detection"]
  version: "1.0.0"
  min-claude-version: "2.1.218"
license: MIT
compatibility: "Requires Python 3.10+, pytest, read/write access to .claude/ directory. Works on any workspace with code/docs/tests."
---

# Self-Audit — Epistemic Calibration & Workspace Knowledge Discovery

## Overview

Most AI failures aren't reasoning errors — they're **calibration errors**. The model confidently assumes a pattern holds, a convention exists, or a library behaves a certain way, but the workspace reality differs. This skill makes those assumptions **explicit, testable, and learnable**.

**Objective:** Transform "I thought X was true" into "X is false (confirmed), here's the evidence, here's the corrected pattern, and here's the memory artifact so I don't relearn it."

This is not `universal-brainstorming` (topic-driven discovery) nor `doubt-driven-development` (decision-stress-testing). This is **continuous epistemic hygiene** for the model-workspace interface.

## When to Use

**Use when:**
- Starting a new session in a workspace (cold start calibration)
- Before major implementation tasks (load known blind spots via `using-agent-skills` pre-check)
- Confidence feels uncalibrated — "I keep being surprised by the same things"
- Workspace conventions are implicit and undocumented
- Cross-session learning keeps resetting (memory not persisting effectively)
- You need to audit your own knowledge boundaries before claiming expertise

**Do NOT use for:**
- Simple factual questions (use web search / direct knowledge)
- Straightforward implementation with clear specs
- Urgent debugging where diagnostic runtime data is needed
- Pure ideation without workspace grounding
- When the workspace has no code/docs/tests to calibrate against

## Core Epistemic Discipline

These rules are non-negotiable. Violating them defeats the skill's purpose.

### 1. Epistemic Status — Classify Every Claim

Every finding, assumption, and conclusion must carry one of these labels:

| Status | Definition | Example |
|--------|------------|---------|
| **FACT** | Directly verified by workspace evidence (test passes, grep matches, doc matches code) | "pytest runs with `python -m pytest`" (verified by running) |
| **WORKSPACE_CONVENTION** | Pattern observed repeatedly in this workspace, not universal | "All handlers use `Result<T, E>` return type" (seen in 12 files) |
| **ASSUMED_FACT** | Model believed true without verification; confidence stated explicitly | "This function returns None on error" (confidence: 0.8) |
| **UNVERIFIED_PATTERN** | Pattern inferred but not systematically checked | "All async functions use `await` correctly" (not grep-verified) |
| **IMPLICIT_CONVENTION** | Unwritten rule discovered via deviation analysis | "Config keys use SCREAMING_SNAKE_CASE" (inferred from 8/10 files) |
| **DOMAIN_GAP** | Missing domain knowledge the workspace assumes | "Songs use verse-chorus structure" (requires domain docs) |
| **CALIBRATION_ERROR** | Confidence ≠ accuracy discovered via test | "Thought `config.get()` raises KeyError; actually returns None" |
| **SPECULATION** | Plausible but insufficient evidence | "This module might be deprecated" (no deprecation marker found) |

**Rule:** Never upgrade a status because it "feels right." Confidence must never increase from repetition alone.

### 2. Confidence Scale — Explicit and Quantitative

Every `ASSUMED_FACT` and `UNVERIFIED_PATTERN` carries a confidence score (0.0–1.0):

- **0.9–1.0**: Would bet significant resources on it
- **0.7–0.89**: Reasonable working assumption, needs verification before committing
- **0.5–0.69**: Weak signal, treat as hypothesis
- **0.3–0.49**: Leaning against, but not ruled out
- **0.0–0.29**: Strongly doubt, but not falsified

Confidence is the **model's internal probability estimate**, not a rhetorical device.

### 3. Abstraction Layer Classification — Required for Every Finding

Every finding must be tagged with its abstraction layer:

| Layer | Scope | Examples |
|-------|-------|----------|
| **L1: Syntax/Local** | Single file, function, line | "Missing type hint on line 42", "Hardcoded string 'TODO'" |
| **L2: Pattern/Module** | Recurring pattern within a module/directory | "All services use dependency injection", "Tests use `arrange-act-assert`" |
| **L3: Architecture/System** | Cross-module, system-wide invariants | "Event-driven architecture with Kafka", "Database per service" |
| **L4: Domain Principle** | Business/domain logic, not code structure | "Songs use verse-chorus structure", "User consent required for data export" |

**Rule:** No finding without L1-L4 tag. L3/L4 findings are higher leverage — prioritize them.

### 4. Verification Is Mandatory for Testable Claims

If `testable=true`, a verification step **must** execute before the finding graduates from `ASSUMED_FACT`/`UNVERIFIED_PATTERN` to `FACT`/`WORKSPACE_CONVENTION` or `CALIBRATION_ERROR`.

Verification methods (in priority order):
1. **Code execution** — Run test, script, grep, type-check
2. **Static analysis** — grep/rg pattern search, AST analysis, config parsing
3. **Document cross-reference** — Compare docstrings/README/ADR vs implementation
4. **Memory/ADR consistency** — Check against persisted memory decisions
5. **Expert/human query** — Only when automated verification impossible

"Seems right" is never sufficient.

### 5. Calibration Data Persists Across Sessions

The calibration log (confidence vs. actual accuracy) is **append-only and persistent**. It builds a model self-awareness profile over time:
- Systematic overconfidence regions (e.g., "I always overestimate my knowledge of test conventions")
- Systematic underconfidence regions
- Domain-specific calibration curves

This data lives in `.claude/knowledge/calibration.log.jsonl` and is loaded at session start.

### 6. Workspace Knowledge ≠ Universal Truth

A convention discovered in this workspace (e.g., "all handlers return `Result`") is **workspace knowledge**, not a universal best practice. Label it `WORKSPACE_CONVENTION` with `scope: "this-project"`. Do not generalize to other projects without explicit cross-project validation.

## Depth Modes

### Quick (~5–10 min)
`Phase 0 → Phase 1 (top 20 assumptions) → Phase 2 (critical only) → Phase 3 → Phase 6`
Output: `BLIND_SPOT_REGISTER` (top 5), `CALIBRATION_REPORT` (summary)

### Standard (~20–30 min)
Full Phase 0–6 workflow. All assumptions extracted, all testable verified, all blind spots mapped, learning units synthesized.
Output: Full artifact suite.

### Deep (default) (~45–60+ min)
Standard + **Cross-Model Validation** (fresh-context adversarial reviewer per `doubt-driven-development`) + **Historical Trend Analysis** (load calibration.log, compute drift, flag recurring miscalibration patterns).
Output: Full artifact suite + `CROSS_MODEL_VALIDATION.log` + `CALIBRATION_TREND_REPORT`.

Default: **deep**

## Workflow (Phase-Based)

### Phase 0 — WORKSPACE MAP (Passive Scan)

**Goal:** Build a read-only model of the workspace — what exists, how it's organized, what conventions are visible.

**Inputs:** Workspace root path (default: `${CLAUDE_PROJECT_DIR}`)

**Actions:**
1. **Inventory** — List: source dirs, test dirs, config files, doc dirs, memory dirs, AGENTS.md, CLAUDE.md, .claude/ structure
2. **Stack Detection** — Languages, frameworks, build tools, test runners, linters, type checkers
3. **Convention Sampling** — Grep 5–10 high-signal patterns per detected stack (naming, error handling, async, config, logging, DI)
4. **Memory Load** — Read `MEMORY.md` + all memory files, ADRs, CLAUDE.md instructions
5. **Implicit Rule Extraction** — From sampled patterns, infer candidate conventions (frequency ≥ 3 occurrences, ≤ 2 exceptions)

**Output:** `WORKSPACE_MODEL.md` + `WORKSPACE_MODEL.json`

**Epistemic Status:** All conventions here are `UNVERIFIED_PATTERN` until Phase 2 verifies.

---

### Phase 1 — ASSUMPTION EXTRACTION (Active Probe)

**Goal:** From the workspace model, extract the model's **implicit assumptions** — things the model "knows" but hasn't verified.

**Input:** `WORKSPACE_MODEL` + model's internal knowledge about this workspace (from prior sessions, training data patterns, etc.)

**Process:** For each convention, pattern, and structural element in the workspace model, generate assumption candidates:

| Assumption Type | Template | Example |
|-----------------|----------|---------|
| **Convention** | "All X follow pattern Y" | "All config files use YAML" |
| **Behavioral** | "Function/module X does Y when Z" | "`generate()` returns a song object" |
| **Invariant** | "Condition X never occurs" | "No raw SQL in core module" |
| **Delegation** | "Library/tool X handles Y" | "pytest-asyncio handles all async test cases" |
| **Architectural** | "System follows pattern X" | "Workspace uses clean architecture layers" |
| **Domain** | "Domain rule X applies" | "All Turkish pop songs use 126 BPM" |

**For each assumption, record:**
```json
{
  "id": "ASSUME-001",
  "type": "CONVENTION|BEHAVIORAL|INVARIANT|DELEGATION|ARCHITECTURAL|DOMAIN",
  "statement": "All config files use YAML",
  "source_evidence": "WORKSPACE_MODEL.conventions[0] (frequency 8)",
  "confidence": 0.85,
  "testable": true,
  "layer": "L2",
  "scope": "workspace",
  "falsifier": "Find a non-YAML config file in active use"
}
```

**Output:** `ASSUMPTION_REGISTER.json` (array of assumption objects)

**Target:** 30–100 assumptions per workspace (deep mode). Prioritize L2/L3/L4.

---

### Phase 2 — CALIBRATION TESTS (Verification)

**Goal:** Test every `testable=true` assumption against workspace evidence.

**For each assumption in `ASSUMPTION_REGISTER` where `testable=true`:**

1. **Design test** — Minimal verification step:
   - `CONVENTION` → `rg`/`grep` pattern search across relevant files
   - `BEHAVIORAL` → Run function/test, inspect return value/side effects
   - `INVARIANT` → Search for counterexamples (grep for anti-pattern)
   - `DELEGATION` → Check library docs / run minimal integration test
   - `ARCHITECTURAL` → Check import graph, directory structure, ADRs
   - `DOMAIN` → Cross-reference with domain docs, memory, examples

2. **Execute test** — Record:
   - `prediction`: What model expected (from assumption statement)
   - `actual`: What test observed
   - `evidence`: File paths, command output, line numbers
   - `confidence_delta`: `actual_confidence - stated_confidence` (where actual_confidence = 1.0 if confirmed, 0.0 if falsified, 0.5 if inconclusive)

3. **Classify result:**
   - `CONFIRMED` → `FACT` or `WORKSPACE_CONVENTION` (confidence → 1.0)
   - `FALSIFIED` → `CALIBRATION_ERROR` (record delta, note direction)
   - `INCONCLUSIVE` → `UNVERIFIED_PATTERN` (confidence unchanged, flag for re-test)

**Output:** `CALIBRATION_LOG.jsonl` (append-one-per-assumption)
```jsonl
{"assumption_id": "ASSUME-001", "timestamp": "2026-10-22T10:30:00Z", "prediction": "All configs YAML", "actual": "Found 2 JSON configs in runtime/", "evidence": ["runtime/config.json", "runtime/secrets.json"], "result": "FALSIFIED", "confidence_delta": -0.85, "new_status": "CALIBRATION_ERROR", "layer": "L2"}
```

**Rule:** Every testable assumption MUST produce a log entry. No silent skips.

---

### Phase 3 — BLIND SPOT MAP (Gap Discovery)

**Goal:** From calibration results, identify and classify blind spots by layer and severity.

**Blind Spot Categories:**

| Category | Definition | Severity |
|----------|------------|----------|
| **CALIBRATION_ERROR** | High confidence assumption falsified | Critical if L3/L4, High if L2, Medium if L1 |
| **UNVERIFIED_CRITICAL** | `testable=true` but test inconclusive, layer L3/L4 | High |
| **IMPLICIT_CONVENTION_GAP** | Pattern exists but undocumented, deviation found | Medium |
| **DOMAIN_GAP** | Missing domain knowledge required by workspace | High if blocks task |
| **MEMORY_DRIFT** | Workspace changed since last memory write | Medium |
| **POSSIBLE_BLIND_SPOT** | Plausible gap not yet established (per UBS rule) | Low, discoverability: Hard |

**For each blind spot, produce:**
```markdown
### BLIND_SPOT-003
- **Category**: CALIBRATION_ERROR
- **Layer**: L3 (Architecture)
- **Severity**: Critical
- **Assumption**: "Workspace uses clean architecture with domain/application/infrastructure layers"
- **Evidence**: Import graph shows core imports runtime directly; no layer separation
- **Confidence Delta**: -0.72 (stated 0.85, actual 0.13)
- **Discoverability**: Easy (import graph analysis)
- **Impact**: Architectural decisions based on false premise
- **Learning Objective**: Learn actual architecture pattern
- **Verification Protocol**: Generate module dependency graph; document actual pattern
- **Integration Point**: `doubt-driven-development` pre-check for architecture decisions
```

**Output:** `BLIND_SPOT_REGISTER.md` (markdown table + detail sections)

**Stop Condition for Quick Mode:** Top 5 blind spots by (severity × layer_weight) where L4=4, L3=3, L2=2, L1=1.

---

### Phase 4 — LEARNABLE UNIT SYNTHESIS

**Goal:** Convert each blind spot into a **learnable unit** — a self-contained knowledge package with verification protocol.

**For each blind spot in `BLIND_SPOT_REGISTER` (priority order):**

```markdown
# LEARNING_UNIT-007
## Learning Objective
Understand workspace's actual module architecture and dependency rules.

## Current Belief (Falsified)
Clean architecture layers (domain/app/infra) — CALIBRATION_ERROR, delta -0.72

## Corrected Understanding (Hypothesis)
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

**Output:** Individual `.md` files in `.claude/knowledge/learning-units/<id>.md`

**Rule:** Every `CRITICAL` and `HIGH` blind spot MUST produce a learning unit. `MEDIUM` if time permits. `LOW` → `POSSIBLE_BLIND_SPOT` log only.

---

### Phase 5 — KNOWLEDGE BASE UPDATE

**Goal:** Persist verified learnings to the project memory system and local knowledge base.

**Actions:**
1. **Write learning unit files** to `.claude/knowledge/learning-units/`
2. **Update memory system** — For each learning unit that represents a durable decision/pattern:
   - Create memory file in `.claude/projects/<proj>/memory/<slug>.md` (frontmatter + body)
   - Update `MEMORY.md` index with wikilink
3. **Update workspace model** — Patch `WORKSPACE_MODEL.md` with verified conventions (status → `FACT`/`WORKSPACE_CONVENTION`)
4. **Append to calibration log** — Already done in Phase 2, but add summary entry

**Memory File Template:**
```markdown
---
name: workspace-architecture-pattern
description: "Workspace uses modular monolith (core=domain, runtime=ops, system=infra), not clean architecture layers"
metadata:
  node_type: memory
  type: project
  originSessionId: <current-session-id>
  modified: <ISO-timestamp>
  layer: L3
  verified: true
  calibration_delta: -0.72
---

Workspace's architecture is a **modular monolith**, not clean architecture layers.

**Evidence:** Import graph shows core imports runtime/ and system/ directly. No layer separation enforced.

**Why this matters:** Architectural decisions assuming clean architecture will be wrong. Dependency direction is mixed.

**How to apply:** When making architecture decisions, assume modular monolith. Domain logic lives in core. Operational concerns in runtime/. Infrastructure in system/. Cross-layer imports are normal here.

**Falsifier:** If a formal architecture doc (ADR) appears enforcing clean layers, this memory is obsolete.
```

**Output:** Updated memory index + new memory files + updated workspace model.

---

### Phase 6 — CALIBRATION REPORT

**Goal:** Synthesize session results into actionable summary for current and future sessions.

**Report Structure:**
```markdown
# SELF-AUDIT REPORT — Workspace — 2026-10-22

## Session Summary
- Mode: deep
- Duration: 47 min
- Cross-model validation: Yes (2 reviewers)
- Historical trend: Loaded 12 prior sessions

## Assumption Statistics
| Metric | Count |
|--------|-------|
| Total assumptions extracted | 67 |
| Testable | 54 |
| Tested | 54 |
| Confirmed | 38 |
| Falsified (CALIBRATION_ERROR) | 12 |
| Inconclusive | 4 |

## Calibration Curve
- Overall accuracy at stated confidence:
  - 0.9–1.0: 78% actual (overconfident by 0.15)
  - 0.7–0.89: 71% actual (overconfident by 0.12)
  - 0.5–0.69: 58% actual (well calibrated)
  - <0.5: 32% actual (underconfident)

- **Systematic overconfidence zones**: L2 conventions (naming, config), L3 architecture
- **Systematic underconfidence zones**: L4 domain knowledge

## Top Blind Spots (by risk = severity × layer_weight)
| Rank | ID | Category | Layer | Severity | Delta | Learning Unit |
|------|-----|----------|-------|----------|-------|---------------|
| 1 | BS-003 | CALIBRATION_ERROR | L3 | Critical | -0.72 | LU-007 ✓ |
| 2 | BS-011 | DOMAIN_GAP | L4 | High | N/A | LU-012 ✓ |
| 3 | BS-005 | UNVERIFIED_CRITICAL | L3 | High | N/A | LU-008 ⏳ |

## Learning Units Produced
- LU-007: Workspace architecture pattern (VERIFIED → PERSISTED)
- LU-012: Domain-specific conventions (VERIFIED → PERSISTED)
- LU-008: Error handling convention (IN_PROGRESS)

## Cross-Model Validation (Deep Mode)
- Reviewer 1: Confirmed 10/12 calibration errors, found 3 additional
- Reviewer 2: Confirmed 9/12, flagged 2 as workspace-specific not universal
- Consensus: Architecture pattern and domain conventions are highest leverage

## Calibration Trend (Historical)
- Sessions tracked: 12
- Overall calibration improving: mean |delta| decreased from 0.31 → 0.18
- Persistent weak spot: L2 config conventions (recurring in 8/12 sessions)
- New improvement: L4 domain knowledge — first session with structured capture

## Pre-Load Recommendations for Next Session
1. Load `WORKSPACE_MODEL.md` + `workspace-architecture-pattern` memory
2. Load `domain-conventions` memory (LU-012)
3. Flag: Error handling convention still unverified (LU-008) — test early
4. Re-verify: Config format assumption — workspace changed

## Open Questions
- Does core have a formal plugin/extension system? (BS-014, POSSIBLE)
- Are there undocumented CLI commands beyond argparse help? (BS-018, POSSIBLE)

## Stop Reason
**STOP B**: All L3/L4 blind spots have learning units with `VERIFIED` status.
```

**Output:** `CALIBRATION_REPORT.md` (displayed to user) + `CALIBRATION_SUMMARY.json` (machine-readable for `using-agent-skills` pre-check)

---

## Output Artifacts Summary

| Artifact | Format | Location | Purpose |
|----------|--------|----------|---------|
| `WORKSPACE_MODEL.md/.json` | Markdown + JSON | `${KNOWLEDGE_ROOT}/workspace-model.md` | Workspace snapshot for context loading |
| `ASSUMPTION_REGISTER.json` | JSON array | `${KNOWLEDGE_ROOT}/assumptions.json` | Audit trail of what was assumed |
| `CALIBRATION_LOG.jsonl` | JSONL (append-only) | `${KNOWLEDGE_ROOT}/calibration.log.jsonl` | Persistent calibration history |
| `BLIND_SPOT_REGISTER.md` | Markdown | `${KNOWLEDGE_ROOT}/blind-spots.md` | Prioritized gap map |
| `LEARNING_UNITS/*.md` | Markdown | `${KNOWLEDGE_ROOT}/learning-units/<id>.md` | Verified, testable knowledge packages |
| `CROSS_MODEL_VALIDATION.log` | JSONL | `${KNOWLEDGE_ROOT}/cross-model-validation.log.jsonl` | Deep mode adversarial review log |
| `CALIBRATION_REPORT.md` | Markdown | Session output (displayed) | Human-readable summary |
| `MEMORY.md` + memory files | Markdown + YAML | `${MEMORY_ROOT}/` | Durable cross-session knowledge |

**Location Convention:**
- `KNOWLEDGE_ROOT` = `${CLAUDE_PROJECT_DIR}/.claude/knowledge/` (configurable via `--output-dir`)
- `MEMORY_ROOT` = `${CLAUDE_PROJECT_DIR}/.claude/projects/<slug>/memory/` where `<slug>` is sanitized project path
- Both configurable via environment variables `SELF_AUDIT_KNOWLEDGE_ROOT` and `SELF_AUDIT_MEMORY_ROOT`

---

## Integration with Existing Skills

| Skill | Integration |
|-------|-------------|
| `using-agent-skills` | **Pre-check hook**: Before any major task, run `self-audit` quick mode; load `CALIBRATION_SUMMARY.json` + top 3 learning units into context |
| `doubt-driven-development` | **Doubt seeds**: Feed `BLIND_SPOT_REGISTER` (L3/L4 only) as adversarial review targets |
| `context-engineering` | **Context load**: `WORKSPACE_MODEL` + high-priority `LEARNING_UNITS` as primary context |
| `universal-brainstorming` | **PROBE input**: Use `BLIND_SPOT_REGISTER` as blind spot seeds; use `ASSUMPTION_REGISTER` as assumption hunt input |
| `spec-driven-development` | **Assumption validation**: Cross-reference spec assumptions against `CALIBRATION_LOG` |
| `code-review-and-quality` | **Calibration check**: Flag overconfident comments, unverified assumptions in reviewed code |
| `planning-and-task-breakdown` | **Risk input**: Use blind spot severity to weight task risk estimates |

---

## Anti-Patterns (NEVER)

1. **Claiming unknown-unknown discovery** — Only surface as `POSSIBLE_BLIND_SPOT` with `discoverability: Hard`
2. **Skipping verification** — "It's obvious" is not a verification result
3. **Silent confidence inflation** — Confidence must be explicit and can only increase via verification
4. **Generalizing workspace conventions** — Tag with `scope: "this-project"` always
5. **Conflating model knowledge with workspace knowledge** — Distinguish "Python uses indentation" (universal) from "This project uses 4-space indent" (workspace)
6. **Fake precision** — Numerical scores without data (use HIGH/MEDIUM/LOW for prioritization unless calibrated)
7. **Premature generalization** — One counterexample ≠ pattern broken; require systematic check
8. **Silent revision** — Changing conclusions without marking revision in log
9. **Ritual calibration** — Running phases without genuine probes; if workspace is stable and calibration log shows low drift, quick mode is correct
10. **Ignoring cross-model disagreement** — If fresh-context reviewer disagrees, log it as `CONTRADICTION` in calibration log

---

## Stop Conditions

Do not run indefinitely. Stop when ANY true:

- **STOP A**: Workspace model stable; calibration drift < 0.05 over last 3 sessions; no new critical blind spots
- **STOP B**: All L3/L4 blind spots have learning units with `VERIFIED` status
- **STOP C**: Next useful step is execution (user wants to build, not audit)
- **STOP D**: Additional phases producing repetition (no new blind spots in 2 consecutive phases)
- **STOP E**: User has enough information to act

When stopping: **State what remains unknown** — list `POSSIBLE_BLIND_SPOT`s and `UNVERIFIED_CRITICAL`s explicitly.

---

## Machine-Readable Output (for tooling)

When structured consumption needed (e.g., `using-agent-skills` pre-check):

```json
{
  "skill": "self-audit",
  "mode": "quick|standard|deep",
  "workspace": "${CLAUDE_PROJECT_DIR}",
  "session_id": "uuid",
  "timestamp": "ISO8601",
  "workspace_model": { ... },
  "assumptions": [
    {"id": "...", "type": "...", "statement": "...", "confidence": 0.85, "testable": true, "layer": "L2", "result": "CONFIRMED|FALSIFIED|INCONCLUSIVE", "confidence_delta": -0.12, "evidence": [...]}
  ],
  "blind_spots": [
    {"id": "...", "category": "...", "layer": "L3", "severity": "Critical", "confidence_delta": -0.72, "learning_unit_id": "...", "status": "PENDING|IN_PROGRESS|VERIFIED|PERSISTED"}
  ],
  "learning_units": [
    {"id": "...", "objective": "...", "verification_protocol": "...", "artifact_path": "...", "memory_pointer": "...", "integration_points": ["doubt-driven-development", "context-engineering"], "status": "VERIFIED"}
  ],
  "calibration_summary": {
    "total": 67, "tested": 54, "confirmed": 38, "falsified": 12, "inconclusive": 4,
    "overconfidence_zones": ["L2 conventions", "L3 architecture"],
    "underconfidence_zones": ["L4 domain"]
  },
  "cross_model_validation": {
    "reviewers": 2,
    "agreement_rate": 0.83,
    "additional_findings": 3
  },
  "recommended_preload": [
    "workspace-model",
    "workspace-architecture-pattern",
    "domain-conventions"
  ],
  "open_questions": [...],
  "stop_reason": "STOP B"
}
```

Machine-readable output MUST preserve epistemic status. Do not encode hypotheses as facts.

---

## Quick Reference Card

| Phase | Quick | Standard | Deep | Key Output |
|-------|-------|----------|------|------------|
| 0: Workspace Map | ✓ | ✓ | ✓ | `WORKSPACE_MODEL` |
| 1: Assumption Extraction | Top 20 | All | All + cross-model seeds | `ASSUMPTION_REGISTER` |
| 2: Calibration Tests | Critical only | All testable | All + adversarial re-test | `CALIBRATION_LOG` |
| 3: Blind Spot Map | Top 5 | All | All + trend analysis | `BLIND_SPOT_REGISTER` |
| 4: Learnable Units | Critical only | High+ | All + cross-model design | `LEARNING_UNITS/` |
| 5: Knowledge Base Update | Memory only | Full | Full + global sync prep | Memory files |
| 6: Calibration Report | Summary | Full | Full + trend + validation | `CALIBRATION_REPORT` |

---

## Final Definition

**Self-Audit** is a structured epistemic calibration process that:
1. Maps the workspace as the model understands it
2. Extracts and makes explicit the model's implicit assumptions
3. Tests assumptions against workspace evidence
4. Maps calibration errors and blind spots by abstraction layer
5. Synthesizes verified learnings into testable, reusable knowledge artifacts
6. Persists calibrated knowledge to project memory for cross-session continuity
7. Tracks calibration trends over time to build model self-awareness

**Primary objective:** Reduce the gap between what the model *thinks* it knows about the workspace and what is *actually true* — turning surprises into durable knowledge.

> SELF-AUDIT = CONTINUOUS EPISTEMIC HYGIENE FOR THE MODEL-WORKSPACE INTERFACE.
> CALIBRATION IS NOT A ONE-TIME EVENT; IT'S A PERSISTENT LOOP.

## Additional Resources

- For complete API details, see [reference.md](reference.md)
- For usage examples, see [examples.md](examples.md)
- For output templates, see [templates/](templates/)