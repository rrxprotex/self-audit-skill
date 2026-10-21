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
  "stack": {
    "languages": ["string"],
    "frameworks": ["string"],
    "build_tools": ["string"],
    "test_runners": ["string"],
    "linters": ["string"],
    "type_checkers": ["string"]
  },
  "structure": {
    "source_dirs": ["string"],
    "test_dirs": ["string"],
    "config_files": ["string"],
    "doc_dirs": ["string"],
    "memory_dirs": ["string"],
    "claude_files": ["string"]
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
    "type": "CONVENTION|BEHAVIORAL|INVARIANT|DELEGATION|ARCHITECTURAL|DOMAIN",
    "statement": "string",
    "source_evidence": "string",
    "confidence": 0.85,
    "testable": true,
    "layer": "L1|L2|L3|L4",
    "scope": "workspace|universal",
    "falsifier": "string",
    "epistemic_status": "ASSUMED_FACT|UNVERIFIED_PATTERN"
  }
]
```

### CALIBRATION_LOG.jsonl (one record per line)

```json
{
  "assumption_id": "ASSUME-001",
  "timestamp": "2026-10-22T10:30:00Z",
  "prediction": "string",
  "actual": "string",
  "evidence": ["string"],
  "result": "CONFIRMED|FALSIFIED|INCONCLUSIVE",
  "confidence_delta": -0.12,
  "new_status": "FACT|WORKSPACE_CONVENTION|CALIBRATION_ERROR|UNVERIFIED_PATTERN",
  "layer": "L2",
  "verification_method": "grep|test_execution|doc_crossref|memory_check|expert_query",
  "session_id": "uuid"
}
```

### BLIND_SPOT_REGISTER.md (also machine-readable JSON)

```json
[
  {
    "id": "BS-001",
    "category": "CALIBRATION_ERROR|UNVERIFIED_CRITICAL|IMPLICIT_CONVENTION_GAP|DOMAIN_GAP|MEMORY_DRIFT|POSSIBLE_BLIND_SPOT",
    "layer": "L1|L2|L3|L4",
    "severity": "Critical|High|Medium|Low",
    "assumption_id": "ASSUME-001",
    "assumption_statement": "string",
    "evidence_summary": "string",
    "confidence_delta": -0.72,
    "discoverability": "Easy|Moderate|Hard",
    "impact": "string",
    "learning_objective": "string",
    "verification_protocol": "string",
    "integration_points": ["string"],
    "learning_unit_id": "LU-001",
    "status": "NEW|IN_PROGRESS|LEARNING_UNIT_CREATED|VERIFIED|PERSISTED"
  }
]
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

## Corrected Understanding (Hypothesis)
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
| `output-dir` | `string` | Override knowledge root |

### Example Invocations

```bash
# Quick mode on current project
/self-audit --mode quick

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