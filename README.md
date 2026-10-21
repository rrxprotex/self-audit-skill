# Self-Audit — Epistemic Calibration Skill for Claude Code

[![License: MIT](https://img.shields.io/badge/License-MIT-yellow.svg)](LICENSE)
[![Claude Code](https://img.shields.io/badge/Claude%20Code-Skill-blue.svg)](https://docs.anthropic.com/en/docs/claude-code/skills)
[![Validation](https://github.com/rrxprotex/self-audit-skill/actions/workflows/validate.yml/badge.svg)](https://github.com/rrxprotex/self-audit-skill/actions/workflows/validate.yml)
[![Evals](https://github.com/rrxprotex/self-audit-skill/actions/workflows/eval.yml/badge.svg)](https://github.com/rrxprotex/self-audit-skill/actions/workflows/eval.yml)

> **Continuous epistemic hygiene for the model-workspace interface.**

Self-Audit is a structured epistemic calibration skill that discovers what the model *doesn't know it doesn't know* within a workspace. It makes implicit assumptions explicit, tests them against evidence, maps calibration errors and blind spots by abstraction layer, and persists verified knowledge for cross-session continuity.

## The Problem

Most AI failures aren't reasoning errors — they're **calibration errors**. The model confidently assumes:
- "This project uses clean architecture" → actually a modular monolith
- "All handlers return `Result<T, E>`" → actually 6 different error patterns
- "Config is YAML" → actually JSON + YAML + env vars mixed
- "Self-improvement uses RL" → actually heuristic optimization

These **unknown unknowns** cause repeated surprises, wasted effort, and architectural mistakes. Self-Audit turns them into **durable, testable knowledge**.

## Features

| Feature | Description |
|---------|-------------|
| **6-Phase Pipeline** | Workspace Map → Assumption Extraction → Calibration Tests → Blind Spot Map → Learnable Units → Knowledge Base Update → Calibration Report |
| **3 Depth Modes** | Quick (5-10 min), Standard (20-30 min), Deep (45-60+ min with cross-model validation + trend analysis) |
| **Abstraction Layer Classification** | Every finding tagged L1 (Syntax) → L2 (Pattern) → L3 (Architecture) → L4 (Domain) |
| **Epistemic Status Taxonomy** | FACT, WORKSPACE_CONVENTION, ASSUMED_FACT, UNVERIFIED_PATTERN, IMPLICIT_CONVENTION, DOMAIN_GAP, CALIBRATION_ERROR, SPECULATION |
| **Persistent Calibration Log** | Append-only JSONL tracking confidence vs accuracy across sessions |
| **Cross-Model Validation** | Deep mode spawns fresh-context adversarial reviewers |
| **Historical Trend Analysis** | Tracks calibration improvement over sessions |
| **Memory Integration** | Writes verified learnings to project memory system (`.claude/projects/<proj>/memory/`) |
| **Skill Integration** | Pre-check for `using-agent-skills`, doubt seeds for `doubt-driven-development`, context for `context-engineering` |

## Quick Start

### Install (One-liner, requires Claude Code v2.1.292+)

```bash
claude plugin install self-audit@rrxprotex/self-audit-skill --marketplace rrxprotex/self-audit-skill
```

### Or Two-Step

```bash
# Add marketplace
claude plugin marketplace add rrxprotex/self-audit-skill --scope project

# Install skill
claude plugin install self-audit@self-audit-marketplace
```

### Use

```bash
# Quick calibration at session start (5-10 min)
/self-audit --mode quick

# Full calibration before major work (20-30 min)
/self-audit --mode standard

# Maximum calibration with cross-model validation (45-60 min)
/self-audit --mode deep

# Custom workspace/output
/self-audit --mode deep --workspace /path/to/project --output-dir /custom/knowledge
```

## Example Output

### Calibration Report (Quick Mode)

```markdown
# SELF-AUDIT REPORT — MyProject — 2026-10-22 (Quick Mode)

## Top 5 Blind Spots
| Rank | ID | Category | Layer | Severity | Delta |
|------|-----|----------|-------|----------|-------|
| 1 | BS-003 | CALIBRATION_ERROR | L3 | Critical | -0.68 |
| 2 | BS-007 | UNVERIFIED_CRITICAL | L4 | High | N/A |
| 3 | BS-002 | CALIBRATION_ERROR | L2 | High | -0.55 |

## Pre-Load for This Session
1. Load WORKSPACE_MODEL.md (updated)
2. Load memory: architecture-pattern (L3 correction)
3. Load memory: error-handling-convention (L2)
```

### Blind Spot Detail

```markdown
### BS-003 — Critical L3 CALIBRATION_ERROR
- **Assumption**: "Project uses clean architecture layers"
- **Evidence**: Import graph shows core imports runtime directly; no layer separation
- **Impact**: Architectural decisions based on false premise
- **Learning Objective**: Learn actual architecture pattern
- **Verification Protocol**: Generate module dependency graph
- **Integration Point**: doubt-driven-development pre-check
```

## Architecture

```
┌─────────────────────────────────────────────────────────────────┐
│                    SELF-AUDIT PIPELINE                          │
├─────────────────────────────────────────────────────────────────┤
│  Phase 0: WORKSPACE MAP      →  WORKSPACE_MODEL.md/.json       │
│  Phase 1: ASSUMPTION EXTRACTION  →  ASSUMPTION_REGISTER.json   │
│  Phase 2: CALIBRATION TESTS    →  CALIBRATION_LOG.jsonl        │
│  Phase 3: BLIND SPOT MAP       →  BLIND_SPOT_REGISTER.md       │
│  Phase 4: LEARNABLE UNITS      →  LEARNING_UNITS/*.md          │
│  Phase 5: KNOWLEDGE BASE UPDATE  →  Memory files               │
│  Phase 6: CALIBRATION REPORT   →  CALIBRATION_REPORT.md + JSON │
└─────────────────────────────────────────────────────────────────┘
```

## Configuration

### Environment Variables

| Variable | Default | Description |
|----------|---------|-------------|
| `SELF_AUDIT_MODE` | `deep` | Default depth mode |
| `SELF_AUDIT_WORKSPACE` | `${CLAUDE_PROJECT_DIR}` | Workspace root |
| `SELF_AUDIT_KNOWLEDGE_ROOT` | `${WORKSPACE}/.claude/knowledge/` | Artifacts output |
| `SELF_AUDIT_MEMORY_ROOT` | `${WORKSPACE}/.claude/projects/<slug>/memory/` | Memory system |
| `SELF_AUDIT_CROSS_MODEL` | `true` | Enable cross-model validation |
| `SELF_AUDIT_TREND_ANALYSIS` | `true` | Enable historical trends |
| `SELF_AUDIT_VERBOSE` | `false` | Verbose logging |

### Skill Arguments

```bash
/self-audit --mode quick|standard|deep --workspace PATH --output-dir PATH
```

## Integration with Other Skills

| Skill | Integration |
|-------|-------------|
| `using-agent-skills` | Pre-check hook: run quick mode before major tasks |
| `doubt-driven-development` | Feed L3/L4 blind spots as doubt seeds |
| `context-engineering` | Load WORKSPACE_MODEL + top learning units |
| `universal-brainstorming` | Use blind spots as PROBE seeds |
| `spec-driven-development` | Validate spec assumptions against calibration log |
| `code-review-and-quality` | Flag overconfident comments, unverified assumptions |

## Project Structure

```
self-audit-skill/
├── .claude-plugin/
│   ├── plugin.json          # Plugin manifest
│   └── marketplace.json     # Marketplace catalog
├── skills/
│   └── self-audit/
│       ├── SKILL.md         # Main skill (Claude Code format)
│       ├── reference.md     # Detailed API/architecture reference
│       ├── examples.md      # Usage examples
│       └── scripts/
│           ├── run-self-audit.py        # CLI wrapper
│           ├── calibration-analytics.py # Log analysis
│           └── validate-assumptions.py  # Standalone validator
├── templates/               # Output artifact templates
├── evals/                   # Eval cases for claude plugin eval
├── .github/workflows/       # CI/CD (validate, eval, release)
├── docs/                    # Documentation
├── LICENSE                  # MIT
├── CONTRIBUTING.md          # Contribution guidelines
├── CHANGELOG.md             # Version history
└── README.md                # This file
```

## Requirements

- **Claude Code** v2.1.218+ (for `context: fork`, `background: true`)
- **Python** 3.10+ (for CLI scripts)
- **rg/ripgrep** (for convention sampling)
- Read/write access to `.claude/` directory

## Documentation

- [Architecture](docs/architecture.md) — Pipeline internals, data flow
- [Configuration](docs/configuration.md) — All config options, env vars
- [Integration](docs/integration.md) — Skill integrations, memory adapter
- [Troubleshooting](docs/troubleshooting.md) — Common issues and fixes

## Contributing

See [CONTRIBUTING.md](CONTRIBUTING.md) for guidelines.

## License

MIT License — see [LICENSE](LICENSE) for details.

## Related

- [Claude Code Skills Documentation](https://docs.anthropic.com/en/docs/claude-code/skills)
- [Agent Skills Specification](https://agentskills.io/specification)
- [awesome-claude-code](https://github.com/anthropics/awesome-claude-code)

---

**Built for continuous epistemic hygiene. Calibration is not a one-time event — it's a persistent loop.**