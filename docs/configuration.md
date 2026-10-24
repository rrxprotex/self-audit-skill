# Self-Audit Skill — Configuration Reference

## Overview

The Self-Audit skill is configured through multiple layers with clear precedence:

1. **Defaults** (built into skill)
2. **Environment Variables** (highest precedence for automation)
3. **Skill Arguments** (CLI flags, override env vars)
4. **Workspace Config** (future: `.self-audit.yaml` in workspace root)

## Environment Variables

| Variable | Default | Type | Description |
|----------|---------|------|-------------|
| `SELF_AUDIT_MODE` | `deep` | `quick\|standard\|deep` | Default depth mode (derived from `SELF_AUDIT_STAKES` when `--stakes` is given) |
| `SELF_AUDIT_WORKSPACE` | `${CLAUDE_PROJECT_DIR}` | path | Workspace root to audit |
| `SELF_AUDIT_KNOWLEDGE_ROOT` | `${WORKSPACE}/.claude/knowledge/` | path | Output directory for artifacts |
| `SELF_AUDIT_MEMORY_ROOT` | `${WORKSPACE}/.claude/projects/<slug>/memory/` | path | Memory system root |
| `SELF_AUDIT_TARGET` | `workspace` | `workspace\|plan\|diff\|last-answer` | What is being audited (§7) |
| `SELF_AUDIT_STAKES` | `medium` | `low\|medium\|high` | Verification budget; sets default mode (low→quick, medium→standard, high→deep) |
| `SELF_AUDIT_SESSION_ID` | auto (`session-YYYYMMDD-HHMMSS`) | string | Session id used to group calibration records in trend analysis |
| `SELF_AUDIT_CROSS_MODEL` | `true` | boolean | Enable cross-model validation (deep) |
| `SELF_AUDIT_TREND_ANALYSIS` | `true` | boolean | Enable historical trend analysis (deep) |
| `SELF_AUDIT_EXTERNAL_REVIEWERS` | unset | JSON | Real external reviewer commands (deep); unset = `NOT_RUN`, never fabricated |
| `SELF_AUDIT_TREND_MIN_SESSIONS` | `2` | integer | Min sessions before trend direction is computed |
| `SELF_AUDIT_MAX_ASSUMPTIONS` | `0` (mode default) | integer | Cap assumptions extracted/tested (0 = mode budget: quick 10 / standard 25 / deep 50) |
| `SELF_AUDIT_QUICK_TOP_N` | `5` | integer | Blind spots ranked in quick mode |
| `SELF_AUDIT_BLIND_SPOT_THRESHOLD` | `0.3` | float | Min \|confidence_delta\| for blind spot |
| `SELF_AUDIT_USER_CONTEXT` | `false` | boolean | Also discover & calibrate user-context assumptions |
| `SELF_AUDIT_VERBOSE` | `false` | boolean | Verbose logging |
| `SELF_AUDIT_CALIBRATION_LOG_VERSION` | `1` | integer | Schema version for calibration log |
| `SELF_AUDIT_DOMAIN_LAYER` | `true` | boolean | Domain-adaptive analysis layer (v1.3); `false` disables entirely |
| `SELF_AUDIT_AUDIT_PURPOSE` | `''` | string | Stated outcome for task resolution (`--audit-purpose`); empty = inferred, labeled |
| `SELF_AUDIT_EXTERNAL_REVIEWERS` | unset | JSON | `[{"name": "r1", "command": "my-review-cmd"}]` — real reviewer commands (deep); unset = `NOT_RUN`, never fabricated |

**Budget rule (Depth Modes):** quick tests 10 assumptions / standard 25 / deep 50, chosen by
verification priority (risk = impact × (1 − confidence)), plus every load-bearing claim.
`SELF_AUDIT_MAX_ASSUMPTIONS` overrides the budget; under `--stakes high` load-bearing (L3/L4)
claims are checked in full regardless of budget (stakes-cap-wins). Assumptions deferred over
budget are counted and reported — never silently dropped.

### Boolean Values

Accepted: `true`, `false`, `yes`, `no`, `on`, `off`, `1`, `0` (case-insensitive)

### Path Resolution

- Relative paths resolved from `${CLAUDE_PROJECT_DIR}` or `--workspace`
- `~` expanded to user home directory
- Environment variables in paths expanded (e.g., `$HOME/.audit`)

## Skill Arguments (Frontmatter `arguments`)

```yaml
arguments: "mode workspace target stakes output-dir user-context"
```

| Argument | Type | Description | Overrides |
|----------|------|-------------|-----------|
| `mode` | `quick\|standard\|deep` | Depth mode (explicit value overrides stakes-derived default) | `SELF_AUDIT_MODE` |
| `workspace` | path | Workspace root | `SELF_AUDIT_WORKSPACE` |
| `target` | `workspace\|plan\|diff\|last-answer` | What is being audited (§7) | `SELF_AUDIT_TARGET` |
| `stakes` | `low\|medium\|high` | Verification budget; sets default mode | `SELF_AUDIT_STAKES` |
| `output-dir` | path | Knowledge artifacts output | `SELF_AUDIT_KNOWLEDGE_ROOT` |
| `user-context` | flag | Enable user-context discovery & calibration | `SELF_AUDIT_USER_CONTEXT` |
| `audit-purpose` | string | Stated outcome for task resolution | `SELF_AUDIT_AUDIT_PURPOSE` |

Also available on `validate-assumptions.py`: `--append` (append to `--output` instead of truncating — use when targeting the append-only `calibration.log.jsonl`), `--concepts PATH` (domain-model JSON for lexical `CANDIDATE_CONFUSION` nomination).

### Usage Examples

```bash
# Via skill invocation
/self-audit --mode quick --workspace /path/to/project --output-dir /custom/output

# Audit a plan instead of the workspace, at high stakes (stakes pick the mode: deep)
/self-audit --target plan --stakes high "the plan text or a path"

# Via environment variables
export SELF_AUDIT_MODE=standard
export SELF_AUDIT_WORKSPACE=/path/to/project
/self-audit

# Mixed
SELF_AUDIT_VERBOSE=true /self-audit --mode deep --output-dir /tmp/audit
```

## Configuration File (Future: `.self-audit.yaml`)

Planned for v1.1.0 — workspace-local configuration:

```yaml
# .self-audit.yaml
mode: standard
knowledge_root: ".claude/knowledge/"
memory_root: ".claude/projects/my-project/memory/"

conventions:
  - pattern: "config files use YAML"
    weight: 1.0
  - pattern: "error handling uses Result<T,E>"
    weight: 0.8

assumption_types:
  - CONVENTION
  - BEHAVIORAL
  - ARCHITECTURAL
  # - INVARIANT (disabled)
  # - DELEGATION (disabled)
  # - DOMAIN (disabled)

depth_modes:
  quick:
    max_assumptions: 10
    test_critical_only: true
    top_blind_spots: 5
  standard:
    max_assumptions: 25
    test_critical_only: false
    top_blind_spots: 15
  deep:
    max_assumptions: 50
    cross_model_reviewers: 2
    trend_analysis: true
    top_blind_spots: 15

output:
  formats: [markdown, json]
  calibration_log: true
  trend_report: true
  cross_model_log: true

integrations:
  using_agent_skills: true
  doubt_driven_development: true
  context_engineering: true
```

## CLI Script Configuration

### `run-self-audit.py`

```bash
python run-self-audit.py \
  --mode quick|standard|deep \
  --workspace /path/to/project \
  --target workspace|plan|diff|last-answer \
  --stakes low|medium|high \
  --output-dir /path/to/output \
  --no-cross-model \
  --no-trend \
  --user-context \
  --verbose
```

Environment variables also work:
```bash
SELF_AUDIT_MODE=quick SELF_AUDIT_WORKSPACE=/project python run-self-audit.py
```

### `calibration-analytics.py`

```bash
python calibration-analytics.py \
  --log /path/to/calibration.log.jsonl \
  --output /path/to/report.md \
  --json  # Output JSON instead of markdown
```

### `validate-assumptions.py`

```bash
python validate-assumptions.py \
  --assumptions /path/to/assumptions.json \
  --workspace /path/to/project \
  --output /path/to/calibration.log.jsonl
```

## Memory System Configuration

### Project Slug Generation

Default: sanitized workspace directory name
```python
slug = workspace.name.lower().replace(" ", "-").replace(".", "-")
```

### Override via Environment

```bash
# Custom memory root
export SELF_AUDIT_MEMORY_ROOT=/custom/memory/path

# Or symlink (recommended)
ln -s /custom/memory/path .claude/projects/my-project/memory
```

### Memory File Frontmatter

Required fields:
```yaml
---
name: unique-slug
description: "One-line summary"
metadata:
  node_type: memory
  type: project
  originSessionId: session-id
  modified: ISO-timestamp
  layer: L1|L2|L3|L4
  verified: true|false
  calibration_delta: number
---
```

## Calibration Log Schema

### Version 1 (Current)

```json
{
  "assumption_id": "ASSUME-001",
  "timestamp": "2026-10-22T10:30:00Z",
  "prediction": "string",
  "actual": "string",
  "evidence": ["string"],
  "result": "CONFIRMED|FALSIFIED|INCONCLUSIVE|SKIPPED",
  "confidence_delta": -0.72,
  "new_status": "FACT|WORKSPACE_CONVENTION|CALIBRATION_ERROR|UNVERIFIED_PATTERN",
  "layer": "L1|L2|L3|L4",
  "verification_method": "grep|test_execution|doc_crossref|memory_check|expert_query|import_graph_analysis|package_analysis",
  "session_id": "uuid"
}
```

### Future Versions

Version 2 will add:
- `cross_model_verdict`: consensus from reviewers
- `trend_context`: session position in trend
- `falsifier_matched`: whether falsifier pattern was found

## Cross-Model Validation Configuration

| Variable | Default | Description |
|----------|---------|-------------|
| `SELF_AUDIT_EXTERNAL_REVIEWERS` | unset | JSON list of `{"name": str, "command": str}` — real reviewer commands (deep). Each receives the blind-spot payload as JSON on stdin and prints a JSON verdict; unset = `NOT_RUN`, never fabricated |
| `SELF_AUDIT_CROSS_MODEL_TIMEOUT` | `300` | Seconds per reviewer command |

`SELF_AUDIT_CROSS_MODEL_REVIEWERS` is deprecated in v1.3 (superseded by the reviewer list length) but still accepted without error.

## Trend Analysis Configuration

| Variable | Default | Description |
|----------|---------|-------------|
| `SELF_AUDIT_TREND_MIN_SESSIONS` | `3` | Minimum sessions for trend |
| `SELF_AUDIT_TREND_WINDOW` | `3` | Sessions to compare for trend |
| `SELF_AUDIT_TREND_IMPROVEMENT_THRESHOLD` | `0.15` | Mean \|Δ| reduction for "improving" |

## Integration Configuration

### Using-Agent-Skills

Add to `using-agent-skills` skill or as hook:
```yaml
pre_check:
  enabled: true
  mode: quick
  load_top_learning_units: 3
  load_calibration_summary: true
```

### Doubt-Driven-Development

```yaml
doubt_seeds:
  source: blind_spots
  filter_layer: [L3, L4]
  filter_severity: [Critical, High]
```

### Context-Engineering

```yaml
context_load:
  priority_files:
    - WORKSPACE_MODEL.md
    - CALIBRATION_SUMMARY.json
  learning_units:
    min_layer: L2
    status: VERIFIED
    max_count: 5
```

## Troubleshooting Configuration

### Common Issues

| Issue | Solution |
|-------|----------|
| "Permission denied" on `.claude/` | Grant write permission or set custom `SELF_AUDIT_KNOWLEDGE_ROOT` |
| "Workspace not found" | Set `SELF_AUDIT_WORKSPACE` or use `--workspace` |
| "No calibration history" | First run — trend analysis will be empty |
| "Cross-model validation failed" | Set `SELF_AUDIT_CROSS_MODEL=false` or check API quota |
| "Memory system not found" | Create `.claude/projects/<slug>/memory/` or set `SELF_AUDIT_MEMORY_ROOT` |

### Debug Mode

```bash
# Verbose logging
SELF_AUDIT_VERBOSE=true /self-audit --mode quick

# Or with skill
/self-audit --mode quick  # Check skill invocation logs
```

### Dry Run (Future)

```bash
# Planned: validate configuration without executing
/self-audit --dry-run --mode quick
```

## Version Compatibility

| Skill Version | Min Claude Code | Min Python | Calibration Log Schema |
|---------------|-----------------|------------|------------------------|
| 1.0.0 | 2.1.218 | 3.10 | v1 |

## Migration Guide

### From No Config to Configured

1. Set `SELF_AUDIT_WORKSPACE` if not using default
2. Set `SELF_AUDIT_KNOWLEDGE_ROOT` for custom output location
3. Set `SELF_AUDIT_MEMORY_ROOT` for custom memory location
4. Adjust `SELF_AUDIT_MODE` for default depth

### Upgrading Calibration Log Schema

When schema version increments:
1. Old logs remain readable
2. New fields added with defaults
3. Analytics script handles both versions
4. No manual migration needed