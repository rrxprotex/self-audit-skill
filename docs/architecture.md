# Self-Audit Skill — Architecture Documentation

## Overview

The Self-Audit skill implements a **6-phase epistemic calibration pipeline** that runs as a forked subagent in Claude Code. Each phase produces structured artifacts that feed into the next phase, building a complete picture of the model's calibration state for a given workspace.

## Pipeline Architecture

```
┌─────────────────────────────────────────────────────────────────────────────┐
│                         SELF-AUDIT PIPELINE                                 │
├─────────────────────────────────────────────────────────────────────────────┤
│                                                                             │
│  ┌─────────┐    ┌──────────────┐    ┌─────────────┐    ┌───────────────┐  │
│  │ PHASE 0 │───▶│   PHASE 1    │───▶│  PHASE 2    │───▶│   PHASE 3     │  │
│  │WORKSPACE│    │ ASSUMPTION   │    │ CALIBRATION │    │ BLIND SPOT    │  │
│  │   MAP   │    │ EXTRACTION   │    │   TESTS     │    │     MAP       │  │
│  └────┬────┘    └──────┬───────┘    └──────┬──────┘    └───────┬───────┘  │
│       │                │                   │                   │          │
│       ▼                ▼                   ▼                   ▼          │
│  WORKSPACE_     ASSUMPTION_          CALIBRATION_         BLIND_SPOT_    │
│  MODEL.md/.json  REGISTER.json          LOG.jsonl            REGISTER.md  │
│                                                                             │
│  ┌─────────┐    ┌──────────────┐    ┌─────────────┐    ┌───────────────┐  │
│  │ PHASE 4 │───▶│   PHASE 5    │───▶│   PHASE 6   │    │  DEEP MODE    │  │
│  │LEARNABLE│    │ KNOWLEDGE    │    │ CALIBRATION │    │  (Optional)   │  │
│  │ UNITS   │    │ BASE UPDATE  │    │   REPORT    │    │               │  │
│  └────┬────┘    └──────┬───────┘    └──────┬──────┘    └───────┬───────┘  │
│       │                │                   │                   │          │
│       ▼                ▼                   ▼                   ▼          │
│  LEARNING_      MEMORY_              CALIBRATION_         CROSS_MODEL_   │
│  UNITS/*.md     FILES.md              REPORT.md            VALIDATION.log │
│                                                                  TREND_    │
│                                                                  REPORT.md  │
│                                                                             │
└─────────────────────────────────────────────────────────────────────────────┘
```

## Phase Details

### Phase 0: Workspace Map (Passive Scan)

**Purpose**: Build a read-only model of the workspace structure, stack, and visible conventions.

**Inputs**: Workspace root path (`${CLAUDE_PROJECT_DIR}` or `--workspace`)

**Operations**:
1. **Inventory**: Walk directory tree, categorize paths (source, test, config, docs, memory, claude)
2. **Stack Detection**: Identify languages, frameworks, build tools, test runners, linters, type checkers
3. **Convention Sampling**: Grep 5-10 high-signal patterns per detected stack
4. **Memory Load**: Read existing memory files, ADRs, CLAUDE.md
5. **Implicit Rule Extraction**: Infer candidate conventions (frequency ≥3, exceptions ≤2)

**Outputs**:
- `WORKSPACE_MODEL.md` — Human-readable workspace snapshot
- `WORKSPACE_MODEL.json` — Machine-readable structured data

**Epistemic Status**: All conventions are `UNVERIFIED_PATTERN` until Phase 2 verification.

### Phase 1: Assumption Extraction (Active Probe)

**Purpose**: Extract the model's implicit assumptions from the workspace model and internal knowledge.

**Inputs**: `WORKSPACE_MODEL` + model's internal knowledge

**Operations**:
For each convention, pattern, and structural element, generate assumption candidates:

| Assumption Type | Template | Example |
|-----------------|----------|---------|
| Convention | "All X follow pattern Y" | "All config files use YAML" |
| Behavioral | "Function X does Y when Z" | "`generate()` returns song object" |
| Invariant | "Condition X never occurs" | "No raw SQL in core module" |
| Delegation | "Library X handles Y" | "pytest-asyncio handles async tests" |
| Architectural | "System follows pattern X" | "Clean architecture layers" |
| Domain | "Domain rule X applies" | "All songs use 126 BPM" |

**Output**: `ASSUMPTION_REGISTER.json` — Array of assumption objects with:
- `id`, `type`, `statement`, `source_evidence`, `confidence`, `testable`, `layer`, `scope`, `falsifier`, `epistemic_status`

**Target**: 30-100 assumptions (deep mode), prioritize L2/L3/L4.

### Phase 2: Calibration Tests (Verification)

**Purpose**: Test every testable assumption against workspace evidence.

**Operations**:
For each assumption with `testable=true`:
1. **Design Test**: Minimal verification step per assumption type
2. **Execute Test**: Record prediction, actual, evidence, confidence_delta
3. **Classify Result**: CONFIRMED → FACT/WORKSPACE_CONVENTION, FALSIFIED → CALIBRATION_ERROR, INCONCLUSIVE → UNVERIFIED_PATTERN

**Verification Methods** (priority order):
1. Code execution (run test, script, type-check)
2. Static analysis (grep/rg, AST, config parsing)
3. Document cross-reference (docstrings vs implementation)
4. Memory/ADR consistency check
5. Expert/human query (last resort)

**Output**: `CALIBRATION_LOG.jsonl` — Append-only, one record per assumption:
```jsonl
{"assumption_id": "ASSUME-001", "timestamp": "...", "prediction": "...", "actual": "...", "evidence": [...], "result": "FALSIFIED", "confidence_delta": -0.72, "new_status": "CALIBRATION_ERROR", "layer": "L3", "verification_method": "import_graph_analysis", "session_id": "..."}
```

**Rule**: Every testable assumption MUST produce a log entry. No silent skips.

### Phase 3: Blind Spot Map (Gap Discovery)

**Purpose**: Identify and classify blind spots from calibration results.

**Blind Spot Categories**:

| Category | Definition | Severity |
|----------|------------|----------|
| CALIBRATION_ERROR | High confidence assumption falsified | Critical (L3/L4), High (L2), Medium (L1) |
| UNVERIFIED_CRITICAL | Testable but inconclusive, L3/L4 | High |
| IMPLICIT_CONVENTION_GAP | Pattern exists but undocumented, deviation found | Medium |
| DOMAIN_GAP | Missing domain knowledge required | High if blocks task |
| MEMORY_DRIFT | Workspace changed since last memory | Medium |
| POSSIBLE_BLIND_SPOT | Plausible gap not established | Low, discoverability: Hard |

**Risk Score**: `severity_weight × layer_weight` where:
- Layer weights: L4=4, L3=3, L2=2, L1=1
- Severity weights: Critical=4, High=3, Medium=2, Low=1

**Output**: `BLIND_SPOT_REGISTER.md` — Markdown table + detail sections

**Quick Mode Stop**: Top 5 by risk score.

### Phase 4: Learnable Unit Synthesis

**Purpose**: Convert each blind spot into a self-contained knowledge package.

**For each blind spot (priority order)**:
```markdown
# LEARNING_UNIT-NNN
## Learning Objective
## Current Belief (Falsified)
## Corrected Understanding (Hypothesis)
## Verification Protocol
## Success Criteria
## Knowledge Artifact Template
## Status: PENDING → IN_PROGRESS → VERIFIED → PERSISTED
```

**Output**: Individual `.md` files in `.claude/knowledge/learning-units/`

**Rule**: Every CRITICAL/HIGH blind spot MUST produce a learning unit.

### Phase 5: Knowledge Base Update

**Purpose**: Persist verified learnings to memory system and knowledge base.

**Operations**:
1. Write learning unit files to `.claude/knowledge/learning-units/`
2. Update memory system:
   - Create memory file in `.claude/projects/<proj>/memory/<slug>.md`
   - Update `MEMORY.md` index with wikilink
3. Update workspace model with verified conventions
4. Append summary to calibration log

**Memory File Template**:
```markdown
---
name: workspace-architecture-pattern
description: "Workspace uses modular monolith, not clean architecture"
metadata:
  node_type: memory
  type: project
  originSessionId: <session-id>
  modified: <ISO-timestamp>
  layer: L3
  verified: true
  calibration_delta: -0.72
---
Content...
```

### Phase 6: Calibration Report

**Purpose**: Synthesize session results into actionable summary.

**Outputs**:
- `CALIBRATION_REPORT.md` — Human-readable summary
- `CALIBRATION_SUMMARY.json` — Machine-readable for tooling

## Deep Mode Extensions

### Cross-Model Validation

Spawns 2 fresh-context reviewer agents (per `doubt-driven-development` pattern):

1. Each reviewer receives: `BLIND_SPOT_REGISTER` + relevant assumptions + workspace model
2. Reviewer prompt: "Adversarially verify these calibration findings. Find errors, confirm falsifications, identify additional blind spots."
3. Results logged to `CROSS_MODEL_VALIDATION.log.jsonl`

**Consensus Rules**:
- Confirmed: ≥2 reviewers agree on falsification
- Refuted: ≥2 reviewers find assumption was correct
- Partial: Mixed verdicts → log as `CONTRADICTION`
- Additional: New blind spots → add to register

### Historical Trend Analysis

Loads all sessions from `CALIBRATION_LOG.jsonl`, computes:

| Metric | Formula | Interpretation |
|--------|---------|----------------|
| Mean |δ| | Σ\|confidence_delta\| / N | Overall calibration error |
| Overconfidence rate | Count(δ < -0.3) / N | Systematic overconfidence |
| Underconfidence rate | Count(δ > 0.3) / N | Systematic underconfidence |
| Layer-specific drift | Mean \|δ\| per layer | Where model struggles |
| Recurring blind spots | Count same category across sessions | Persistent gaps |
| Calibration improvement | Mean \|δ\| session N vs N-3 | Trend direction |

**Output**: `CALIBRATION_TREND_REPORT.md`

## Data Flow

```
┌──────────────┐     ┌─────────────────┐     ┌──────────────────┐
│   Workspace  │────▶│  Phase 0: Map   │────▶│  WORKSPACE_MODEL │
│   (input)    │     │  (read-only)    │     │  (md + json)     │
└──────────────┘     └─────────────────┘     └────────┬─────────┘
                                                      │
                                                      ▼
┌──────────────┐     ┌─────────────────┐     ┌──────────────────┐
│   Model's    │────▶│  Phase 1:       │────▶│  ASSUMPTION_     │
│  Internal    │     │  Extract        │     │  REGISTER.json   │
│  Knowledge   │     │  Assumptions    │     │                  │
└──────────────┘     └─────────────────┘     └────────┬─────────┘
                                                      │
                                                      ▼
                                              ┌─────────────────┐
                                              │  Phase 2: Test  │
                                              │  Assumptions    │
                                              └────────┬────────┘
                                                       │
                                                       ▼
                                              ┌──────────────────┐
                                              │ CALIBRATION_LOG  │
                                              │ (jsonl, append)  │
                                              └────────┬─────────┘
                                                       │
                                                       ▼
                                              ┌─────────────────┐
                                              │  Phase 3: Map   │
                                              │  Blind Spots    │
                                              └────────┬────────┘
                                                       │
                                                       ▼
                                              ┌──────────────────┐
                                              │ BLIND_SPOT_      │
                                              │ REGISTER.md      │
                                              └────────┬─────────┘
                                                       │
                              ┌────────────────────────┼────────────────────────┐
                              ▼                        ▼                        ▼
                     ┌───────────────┐        ┌───────────────┐        ┌───────────────┐
                     │ Phase 4:      │        │ Phase 5:      │        │ Phase 6:      │
                     │ Synthesize    │        │ Update        │        │ Report        │
                     │ Learnable     │        │ Knowledge     │        │               │
                     │ Units         │        │ Base          │        │               │
                     └───────┬───────┘        └───────┬───────┘        └───────┬───────┘
                             │                        │                        │
                             ▼                        ▼                        ▼
                    ┌───────────────┐        ┌───────────────┐        ┌───────────────┐
                    │ LEARNING_     │        │ MEMORY_       │        │ CALIBRATION_  │
                    │ UNITS/*.md    │        │ FILES.md      │        │ REPORT.md     │
                    └───────────────┘        └───────────────┘        └───────────────┘
```

## Configuration System

### Environment Variables

| Variable | Default | Phase Impact |
|----------|---------|--------------|
| `SELF_AUDIT_MODE` | `deep` | All phases |
| `SELF_AUDIT_WORKSPACE` | `${CLAUDE_PROJECT_DIR}` | Phase 0 |
| `SELF_AUDIT_KNOWLEDGE_ROOT` | `${WORKSPACE}/.claude/knowledge/` | All outputs |
| `SELF_AUDIT_MEMORY_ROOT` | `${WORKSPACE}/.claude/projects/<slug>/memory/` | Phase 5 |
| `SELF_AUDIT_CROSS_MODEL` | `true` | Deep mode only |
| `SELF_AUDIT_TREND_ANALYSIS` | `true` | Deep mode only |
| `SELF_AUDIT_MAX_ASSUMPTIONS` | `100` | Phase 1 |
| `SELF_AUDIT_QUICK_TOP_N` | `20` | Phase 1 (quick) |
| `SELF_AUDIT_BLIND_SPOT_THRESHOLD` | `0.5` | Phase 3 |
| `SELF_AUDIT_VERBOSE` | `false` | All phases |

### Skill Arguments (Frontmatter `arguments`)

| Argument | Type | Overrides |
|----------|------|-----------|
| `mode` | `quick\|standard\|deep` | `SELF_AUDIT_MODE` |
| `workspace` | `string` | `SELF_AUDIT_WORKSPACE` |
| `output-dir` | `string` | `SELF_AUDIT_KNOWLEDGE_ROOT` |

## Integration Points

### Using-Agent-Skills Pre-Check

```bash
# In using-agent-skills discovery flow
/self-audit --mode quick
# Load CALIBRATION_SUMMARY.json + top 3 learning units
```

### Doubt-Driven-Development

```bash
# Feed L3/L4 blind spots as doubt seeds
# BLIND_SPOT_REGISTER.md → filter layer >= L3 → doubt-driven-development
```

### Context-Engineering

```bash
# Primary context files:
# 1. WORKSPACE_MODEL.md
# 2. High-priority LEARNING_UNITS (VERIFIED, layer >= L2)
# 3. CALIBRATION_SUMMARY.json
```

### Spec-Driven-Development

```bash
# Cross-reference spec assumptions against CALIBRATION_LOG
# Any spec assumption matching CALIBRATION_ERROR → flag for review
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