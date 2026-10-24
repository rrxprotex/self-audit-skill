# Self-Audit Skill — Usage Examples

## Example 1: Quick Mode at Session Start

**Scenario:** Starting a new session in a workspace you haven't visited in a while.

```bash
/self-audit --mode quick
```

**Expected Output:**
```
# SELF-AUDIT REPORT — MyProject — 2026-10-22 (Quick Mode)

## Session Summary
- Mode: quick
- Duration: 7 min
- Workspace: /path/to/MyProject

## Top 5 Blind Spots
| Rank | ID | Category | Layer | Severity | Delta |
|------|-----|----------|-------|----------|-------|
| 1 | BS-003 | CALIBRATION_ERROR | L3 | Critical | -0.68 |
| 2 | BS-007 | UNVERIFIED_CRITICAL | L4 | High | N/A |
| 3 | BS-002 | CALIBRATION_ERROR | L2 | High | -0.55 |
| 4 | BS-011 | IMPLICIT_CONVENTION_GAP | L2 | Medium | -0.32 |
| 5 | BS-001 | MEMORY_DRIFT | L1 | Medium | -0.28 |

## Pre-Load for This Session
1. Load WORKSPACE_MODEL.md (updated)
2. Load memory: architecture-pattern (L3 correction)
3. Load memory: error-handling-convention (L2)
4. Flag: Domain conventions unverified (BS-007)

## Stop Reason
STOP C: Next useful step is execution.
```

**Artifacts Created:**
- `.claude/knowledge/workspace-model.md`
- `.claude/knowledge/assumptions.json` (top 20)
- `.claude/knowledge/calibration.log.jsonl` (critical only)
- `.claude/knowledge/blind-spots.md` (top 5)

---

## Example 2: Standard Mode Before Major Refactor

**Scenario:** About to refactor the authentication module — want full calibration first.

```bash
/self-audit --mode standard
```

**Expected Output:** Full calibration report with all assumptions tested, all blind spots mapped, learning units for HIGH+ severity.

**Artifacts Created:** Full suite (all phases 0-6).

---

## Example 3: Deep Mode for New Project Onboarding

**Scenario:** Joining a new codebase, want maximum calibration with cross-model validation.

```bash
/self-audit --mode deep
```

**Deep Mode Adds:**
- Cross-model adversarial validation (2 fresh-context reviewers)
- Historical trend analysis (loads prior calibration.log)
- Consensus verification of all calibration errors
- CALIBRATION_TREND_REPORT.md
- CROSS_MODEL_VALIDATION.log.jsonl

**Expected Duration:** 45-60 minutes.

---

## Example 4: Custom Workspace and Output Directory

```bash
/self-audit --mode deep --workspace /home/user/projects/legacy-system --output-dir /home/user/audit-results
```

**Environment Variable Equivalent:**
```bash
SELF_AUDIT_MODE=deep SELF_AUDIT_WORKSPACE=/home/user/projects/legacy-system SELF_AUDIT_KNOWLEDGE_ROOT=/home/user/audit-results /self-audit
```

---

## Example 5: Integration with using-agent-skills Pre-Check

**In your `using-agent-skills` skill or as a hook:**

```markdown
## Pre-Task Calibration (Auto)

Before any major implementation task:

1. Run quick self-audit:
   `/self-audit --mode quick`

2. Load calibration summary:
   Read `.claude/knowledge/calibration.log.jsonl` (last session)
   Read `.claude/knowledge/blind-spots.md` (top 5)

3. Load top 3 learning units:
   For each LU in blind-spots.md with status VERIFIED:
   Read `.claude/knowledge/learning-units/<id>.md`

4. Feed to context-engineering:
   Context files = [WORKSPACE_MODEL.md, LU-1, LU-2, LU-3, CALIBRATION_SUMMARY.json]
```

**Result:** Every major task starts with calibrated knowledge, not assumptions.

---

## Example 6: Feeding Blind Spots to doubt-driven-development

```bash
# 1. Run self-audit (any mode)
/self-audit --mode standard

# 2. Extract L3/L4 blind spots
# From .claude/knowledge/blind-spots.md, filter layer >= L3

# 3. Invoke doubt-driven-development with blind spots as doubt seeds
/doubt-driven-development --seeds ".claude/knowledge/blind-spots.md#L3" --target "authentication refactor"
```

---

## Example 7: CI/CD Integration

**GitHub Actions (run on PR):**

```yaml
- name: Calibrate workspace
  run: |
    claude plugin install self-audit@marketplace
    /self-audit --mode quick
    
- name: Check for critical blind spots
  run: |
    python -c "
    import json
    with open('.claude/knowledge/blind-spots.md') as f:
        content = f.read()
    # Parse and check for Critical severity L3/L4
    if 'Critical' in content and ('L3' in content or 'L4' in content):
        print('::error::Critical blind spots found - review before merge')
        exit(1)
    "
```

---

## Example 8: Memory Adapter for Non-Standard Memory Systems

**If your project uses a different memory location:**

```bash
# Option 1: Environment variable
SELF_AUDIT_MEMORY_ROOT=/custom/memory/path /self-audit --mode standard

# Option 2: Symlink (recommended)
ln -s /custom/memory/path .claude/projects/my-project/memory
/self-audit --mode standard
```

---

## Example 9: Analyzing Calibration Trends

**After multiple sessions, analyze your calibration history:**

```bash
# Run analytics script
python ${CLAUDE_SKILL_DIR}/scripts/calibration-analytics.py \
  --log .claude/knowledge/calibration.log.jsonl \
  --output calibration-trend-report.md
```

**Output:** Trend report showing calibration improvement over sessions.

---

## Example 10: Validating Assumptions Manually

**Standalone assumption testing (without full pipeline):**

```bash
python ${CLAUDE_SKILL_DIR}/scripts/validate-assumptions.py \
  --assumptions .claude/knowledge/assumptions.json \
  --workspace . \
  --output .claude/knowledge/calibration.log.jsonl \
  --append
```

---

## Example Output Artifacts

### WORKSPACE_MODEL.md (excerpt)

```markdown
# WORKSPACE_MODEL — MyProject (v2.3.1)

## Domain
E-commerce platform with microservices architecture.

## Stack
- Languages: TypeScript, Python, Go
- Frameworks: NestJS, FastAPI, Gin
- Test: Jest, pytest, testify

## Structure
src/
├── services/
│   ├── auth/
│   ├── orders/
│   └── payments/
├── shared/
└── infra/

## Detected Conventions (UNVERIFIED_PATTERN)
1. Config via YAML + env (frequency: 12 files)
2. Error handling: Result<T,E> pattern? (needs verification)
3. Logging: pino (TS), structlog (Py), zerolog (Go)
4. Testing: Unit + integration, contract tests for APIs
```

### ASSUMPTION_REGISTER.json (excerpt)

```json
[
  {
    "id": "ASSUME-001",
    "type": "CONVENTION",
    "statement": "All services use Result<T, E> for error handling",
    "source_evidence": "WORKSPACE_MODEL.conventions[1] (frequency 3)",
    "confidence": 0.75,
    "testable": true,
    "layer": "L2",
    "scope": "workspace",
    "falsifier": "Find a service using try/catch without Result"
  },
  {
    "id": "ASSUME-007",
    "type": "ARCHITECTURAL",
    "statement": "Services communicate via async message queue only",
    "source_evidence": "WORKSPACE_MODEL.structure + ADR-004",
    "confidence": 0.9,
    "testable": true,
    "layer": "L3",
    "scope": "workspace",
    "falsifier": "Find synchronous HTTP calls between services"
  }
]
```

### CALIBRATION_LOG.jsonl (excerpt)

```jsonl
{"assumption_id": "ASSUME-001", "timestamp": "2026-10-22T10:30:00Z", "prediction": "All services use Result<T,E>", "actual": "orders/ uses try/catch; payments/ uses Result; auth/ uses exceptions", "evidence": ["src/services/orders/handler.ts", "src/services/payments/result.ts", "src/services/auth/errors.ts"], "result": "FALSIFIED", "confidence_delta": -0.75, "new_status": "CALIBRATION_ERROR", "layer": "L2", "verification_method": "grep", "session_id": "abc-123"}
{"assumption_id": "ASSUME-007", "timestamp": "2026-10-22T10:30:15Z", "prediction": "Async message queue only", "actual": "Found 3 synchronous REST calls: auth→orders, orders→payments, payments→auth", "evidence": ["src/services/auth/client.ts:45", "src/services/orders/payment.ts:12", "src/services/payments/auth.ts:8"], "result": "FALSIFIED", "confidence_delta": -0.90, "new_status": "CALIBRATION_ERROR", "layer": "L3", "verification_method": "grep", "session_id": "abc-123"}
```

### BLIND_SPOT_REGISTER.md (excerpt)

```markdown
# BLIND SPOT REGISTER — MyProject — 2026-10-22

## Top 5 by Risk (severity × layer_weight)

| Rank | ID | Category | Layer | Severity | Delta | Learning Unit |
|------|-----|----------|-------|----------|-------|---------------|
| 1 | BS-007 | CALIBRATION_ERROR | L3 | Critical | -0.90 | LU-001 |
| 2 | BS-001 | CALIBRATION_ERROR | L2 | High | -0.75 | LU-002 |
| 3 | BS-003 | UNVERIFIED_CRITICAL | L4 | High | N/A | LU-003 |
| 4 | BS-005 | IMPLICIT_CONVENTION_GAP | L2 | Medium | -0.40 | LU-004 |
| 5 | BS-002 | MEMORY_DRIFT | L1 | Medium | -0.25 | LU-005 |

## BS-007 — Critical L3 Calibration Error
- **Assumption**: "Services communicate via async message queue only"
- **Evidence**: 3 synchronous REST calls found (auth→orders, orders→payments, payments→auth)
- **Impact**: Architecture decisions assume eventual consistency; actual system has synchronous dependencies
- **Learning Objective**: Document actual service communication topology
- **Verification Protocol**: Generate service dependency graph; classify sync vs async edges
- **Integration Point**: doubt-driven-development pre-check for architecture changes
```

### LEARNING_UNIT-001.md (excerpt)

```markdown
# LEARNING_UNIT-001

## Learning Objective
Document actual service communication topology (sync + async).

## Current Belief (Falsified)
Async message queue only — CALIBRATION_ERROR, delta -0.90

## Corrected Understanding (Hypothesis)
Hybrid communication: Core domain events via async queue; cross-domain queries via synchronous REST. Three synchronous edges form a cycle (auth→orders→payments→auth).

## Verification Protocol
1. Generate service dependency graph from imports and network calls
2. Classify each edge: async (queue) vs sync (REST/gRPC)
3. Identify cycles in synchronous subgraph
4. Document in ADR-015

## Success Criteria
- Dependency graph generated with edge types
- Synchronous cycles documented
- ADR-015 created with communication pattern decision

## Knowledge Artifact
- **Type**: Architecture Decision Record (ADR)
- **Location**: .claude/knowledge/learning-units/service-communication-topology.md
- **Memory Pointer**: .claude/projects/my-project/memory/service-communication-topology.md
- **Integration**: Tag for doubt-driven-development, context-engineering

## Status: VERIFIED → PERSISTED
```

---

## Troubleshooting Examples

### "Skill not triggering"

```bash
# Check skill is loaded
/skills

# Check frontmatter parses
claude --debug 2>&1 | grep -i "self-audit"

# Re-read skill
/reload-skills
```

### "Permission denied writing to .claude/"

```bash
# Grant permission in settings or run with appropriate scope
# Or set custom output dir:
/self-audit --mode quick --output-dir /tmp/audit-output
```

### "Cross-model validation fails"

```bash
# Disable if not needed
SELF_AUDIT_CROSS_MODEL=false /self-audit --mode deep

# Or use standard mode (no cross-model)
/self-audit --mode standard
```

### "Calibration log grows too large"

```bash
# Archive old sessions
mv .claude/knowledge/calibration.log.jsonl .claude/knowledge/calibration.log.jsonl.2026-Q3
# Skill will start fresh log
```

---

## Quick Reference: Common Invocations

| Goal | Command |
|------|---------|
| Cold start calibration | `/self-audit --mode quick` |
| Pre-refactor calibration | `/self-audit --mode standard` |
| New project onboarding | `/self-audit --mode deep` |
| Specific workspace | `/self-audit --workspace /path/to/project` |
| Custom output | `/self-audit --output-dir /custom/path` |
| CI integration | `SELF_AUDIT_MODE=quick /self-audit` |
| Skip cross-model | `SELF_AUDIT_CROSS_MODEL=false /self-audit --mode deep` |
| Verbose logging | `SELF_AUDIT_VERBOSE=true /self-audit` |