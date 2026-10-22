# Self-Audit — Epistemic Calibration for AI Agents

[![License: MIT](https://img.shields.io/badge/License-MIT-yellow.svg)](LICENSE)
[![Claude Code Skill](https://img.shields.io/badge/Claude%20Code-Skill-blue.svg)](https://docs.anthropic.com/en/docs/claude-code/skills)
[![Validation](https://github.com/rrxprotex/self-audit-skill/actions/workflows/validate.yml/badge.svg)](https://github.com/rrxprotex/self-audit-skill/actions/workflows/validate.yml)
[![Evals](https://github.com/rrxprotex/self-audit-skill/actions/workflows/eval.yml/badge.svg)](https://github.com/rrxprotex/self-audit-skill/actions/workflows/eval.yml)

> **Continuous epistemic hygiene for the model–workspace–user interface.**

Most AI failures in a codebase aren't reasoning errors — they're **calibration errors**. The model confidently assumes a pattern holds, a convention exists, or a library behaves a certain way, and the workspace turns out to be different. Self-Audit makes those hidden assumptions explicit, **tests them against real evidence**, ranks them by risk, and writes the corrections to memory so the same mistake is never relearned.

It also calibrates the *other* side of the interface: what the **user** needs, intends, or knows — even when they can't articulate it — against what the workspace actually requires.

---

## Why this deserves a ⭐

| The pain | What Self-Audit does |
|----------|----------------------|
| "I keep being surprised by the same things in this repo." | Surfaces the **unknown unknowns** and pins them to evidence, not vibes. |
| Every session relearns what the last one figured out. | Persists verified learnings to **project memory** with a real `PENDING → VERIFIED → PERSISTED` lifecycle. |
| You don't know what the model is wrong about until it breaks. | Produces a **ranked blind-spot map** (risk = severity × layer) *before* the work starts. |
| Confidence feels high but accuracy is unknown. | Tracks a **calibration log** (predicted confidence vs. measured outcome) across sessions. |
| It only works in one tool. | **Harness-agnostic core**: pure Python + Markdown/JSONL artifacts — runs in any CLI, TUI, or desktop agent. |

**The one-liner:** turn *"I thought X was true"* into *"X is false (confirmed), here's the evidence, here's the corrected pattern, and here's the memory artifact so I don't relearn it."*

---

## What it produces

Run it once and you get a set of durable artifacts under `.claude/knowledge/`:

| Artifact | What it holds |
|----------|---------------|
| `workspace-model.md` / `.json` | The inferred structure & conventions of the workspace |
| `assumptions.json` | Extracted assumptions, each tagged L1–L4 + epistemic status |
| `calibration.log.jsonl` | Append-only log of prediction → outcome → confidence delta |
| `blind-spots.md` | Blind spots ranked by risk (severity × layer weight) |
| `learning-units/LU-*.md` | Self-contained learnable units with verification protocols |
| `calibration-report.md` / `calibration-summary.json` | Human + machine-readable audit summary |
| `calibration-trend-report.md` | Calibration improvement across sessions (deep mode) |
| `cross-model-validation.log.jsonl` | Adversarial reviewer verdicts (deep mode) |

Every finding is classified along two axes:

- **Abstraction layer** — `L1 Syntax → L2 Pattern → L3 Architecture → L4 Domain`
- **Epistemic status** — `FACT`, `WORKSPACE_CONVENTION`, `ASSUMED_FACT`, `UNVERIFIED_PATTERN`, `IMPLICIT_CONVENTION`, `DOMAIN_GAP`, `CALIBRATION_ERROR`, `SPECULATION`

---

## Example output (real run)

This is genuine output from running Self-Audit **on its own repository**:

```text
[SCAN] Self-Audit starting...
   Workspace: C:\Users\mozarc\self-audit-skill
   Mode: deep

[PHASE] STANDARD MODE: Phase 0 -> 1 -> 2 -> 3 -> 4 -> 5 -> 6
  Phase 0: Mapping workspace...
    Found 0 source dirs, 2 candidate conventions
  Phase 1: Extracting assumptions...
    Extracted 7 assumptions
  Phase 2: Running calibration tests...
    [MEMORY] 1 assumptions already FALSIFIED (skipping re-test)
    [OK] ASSUME-001: CONFIRMED (delta: 0.10)
    [SKIP] ASSUME-003: KNOWN FALSE (from prior sessions)
    ...
    Tested 6 assumptions, skipped 1 known-false
  Phase 3: Mapping blind spots...
    Identified 1 blind spots (top 15), 1 recurring
  Phase 5: Updating knowledge base...
    [PERSISTED] LU-PERSIST-001 (already cross-session verified)
  Deep: Cross-model validation...
    Cross-model validation log written with 2 reviews
  Deep: Historical trend analysis...
    Analyzed 101 calibration records
```

And the resulting **blind-spot register**:

```markdown
| Rank | ID          | Category             | Layer | Severity | Delta | Learning Unit  |
|------|-------------|----------------------|-------|----------|-------|----------------|
| 1    | BS-REC-001  | PERSISTENT_BLIND_SPOT| L3    | Critical | -0.70 | LU-PERSIST-001 |

### BS-REC-001 -- Critical L3 PERSISTENT_BLIND_SPOT
- **Assumption**: Workspace follows Clean architecture layers (domain/app/infra)
- **Evidence**: Import graph shows modular monolith pattern, not clean architecture layers
- **Impact**: RECURRING: 6x falsified across sessions
- **Verification Protocol**: Document l3 convention in ADR and enforce
```

Notice the **self-learning loop**: a previously-falsified assumption (`ASSUME-003`) is *skipped*, not re-tested, and the recurring error is escalated to `PERSISTENT_BLIND_SPOT` with its learning unit marked `PERSISTED`. That continuity is the whole point.

---

## How it works

```text
┌───────────────────────────────────────────────────────────────────────┐
│                     SELF-AUDIT PIPELINE                                │
├───────────────────────────────────────────────────────────────────────┤
│  Phase 0  WORKSPACE MAP          →  workspace-model.md / .json        │
│  Phase 1  ASSUMPTION EXTRACTION  →  assumptions.json                   │
│  Phase 2  CALIBRATION TESTS      →  calibration.log.jsonl             │
│            (skips KNOWN FALSE from prior sessions)                     │
│  Phase 3  BLIND SPOT MAP         →  blind-spots.md                    │
│            (recurring errors → PERSISTENT_BLIND_SPOT)                  │
│  Phase 4  LEARNABLE UNITS        →  learning-units/LU-*.md            │
│  Phase 5  KNOWLEDGE BASE UPDATE  →  memory/ + lifecycle promotion      │
│            (PENDING → VERIFIED → PERSISTED, copies kept in sync)       │
│  Phase 6  CALIBRATION REPORT     →  calibration-report.md + summary   │
└───────────────────────────────────────────────────────────────────────┘
   Deep mode adds:  Cross-model validation  +  Historical trend analysis
```

**Three depth modes** — pick based on how much you need:

| Mode | Pipeline | Extra | Typical use |
|------|----------|-------|-------------|
| `quick` | Phase 0–3 | — | Fast cold-start check at session start |
| `standard` | Phase 0–6 | — | Full audit before major work |
| `deep` | Phase 0–6 | + cross-model validation + trend analysis | Maximum rigor, adversarial review |

---

## Install

**Requirements:** Python 3.10+, read/write access to `.claude/`, Claude Code v2.1.218+ (for `context: fork`, `background: true`).

### Claude Code plugin (one-liner)

```bash
claude plugin install self-audit@rrxprotex/self-audit-skill --marketplace rrxprotex/self-audit-skill
```

### Or two-step

```bash
claude plugin marketplace add rrxprotex/self-audit-skill --scope project
claude plugin install self-audit@self-audit-marketplace
```

### Run

```bash
# Fast check at session start
/self-audit --mode quick

# Full audit before major work
/self-audit --mode standard

# Maximum rigor: cross-model validation + trend analysis
/self-audit --mode deep

# Custom workspace / output
/self-audit --mode deep --workspace /path/to/project --output-dir /custom/knowledge
```

### Direct CLI (harness-agnostic)

The core is a plain Python script — no API key, no Claude dependency. Run it from any agent harness, CI job, or shell:

```bash
python skills/self-audit/scripts/run-self-audit.py --mode deep --workspace /path/to/project
```

```text
usage: run-self-audit.py [-h] [--mode {quick,standard,deep}]
                         [--workspace WORKSPACE] [--output-dir OUTPUT_DIR]
                         [--no-cross-model] [--no-trend] [--verbose]
```

---

## Configuration

Control the run through environment variables — this is what makes it portable across harnesses:

| Variable | Default | Description |
|----------|---------|-------------|
| `SELF_AUDIT_WORKSPACE` | `.` | Workspace root to audit |
| `SELF_AUDIT_KNOWLEDGE_ROOT` | `<workspace>/.claude/knowledge/` | Where artifacts are written |
| `SELF_AUDIT_MEMORY_ROOT` | `<workspace>/.claude/projects/<slug>/memory/` | Memory system root |
| `SELF_AUDIT_CROSS_MODEL` | `true` | Cross-model validation (deep mode) |
| `SELF_AUDIT_TREND_ANALYSIS` | `true` | Historical trend analysis (deep mode) |
| `SELF_AUDIT_VERBOSE` | `false` | Verbose logging |

---

## Works beyond Claude Code

The **epistemic engine is plain Python + Markdown/JSONL**, so it runs anywhere an agent can execute a script and read/write files:

- **Claude Code** — as a native skill (`/self-audit`), with memory + skill integration
- **Codex / OpenCode / Cline / Cursor / Gemini CLI / Hermes** and any CLI, TUI, or desktop agent — invoke `run-self-audit.py` directly, or paste the `SKILL.md` as a system prompt
- **CI** — run the audit on a schedule and diff the blind-spot map between runs

No `ANTHROPIC_API_KEY` required. No LLM judge required for evals — the graders are static.

---

## Integration with other skills

| Skill | How Self-Audit plugs in |
|-------|-------------------------|
| `using-agent-skills` | Pre-check hook: run `quick` before major tasks |
| `doubt-driven-development` | Feed L3/L4 blind spots as doubt seeds |
| `context-engineering` | Load `workspace-model` + top learning units |
| `universal-brainstorming` | Use blind spots as PROBE seeds |
| `spec-driven-development` | Validate spec assumptions against the calibration log |
| `code-review-and-quality` | Flag overconfident comments & unverified assumptions |

---

## Repository structure

```text
self-audit-skill/
├── .claude-plugin/
│   ├── plugin.json          # Plugin manifest
│   └── marketplace.json     # Marketplace catalog
├── skills/self-audit/
│   ├── SKILL.md             # Main skill definition
│   ├── reference.md         # API / architecture reference
│   ├── examples.md          # Usage examples
│   └── scripts/
│       ├── run-self-audit.py        # Core CLI (harness-agnostic)
│       ├── calibration-analytics.py # Log analysis
│       └── validate-assumptions.py  # Standalone validator
├── templates/               # Starter templates for every artifact
├── evals/                   # Eval cases + static graders
├── .github/
│   ├── scripts/eval-runner.py   # Model-agnostic eval runner
│   └── workflows/               # validate, eval, release
├── docs/                    # architecture, configuration, integration, troubleshooting
├── LICENSE  CONTRIBUTING.md  CHANGELOG.md  CODE_OF_CONDUCT.md  SECURITY.md
└── README.md
```

---

## Documentation

- [Architecture](docs/architecture.md) — pipeline internals & data flow
- [Configuration](docs/configuration.md) — every config option & env var
- [Integration](docs/integration.md) — skill integrations & memory adapter
- [Troubleshooting](docs/troubleshooting.md) — common issues & fixes

## Contributing

See [CONTRIBUTING.md](CONTRIBUTING.md). Issues and PRs welcome — especially new convention detectors (TypeScript, Go, Rust, Java) and harness adapters.

## License

MIT — see [LICENSE](LICENSE).

## Related

- [Claude Code Skills](https://docs.anthropic.com/en/docs/claude-code/skills)
- [Agent Skills Specification](https://agentskills.io/specification)
- [awesome-claude-code](https://github.com/anthropics/awesome-claude-code)

---

**Calibration is not a one-time event — it's a persistent loop.** ⭐ If this saves you one debugging surprise, star it and share it.