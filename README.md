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
| `analysis-findings.json` | **v1.3** domain-layer report: task resolution, findings, pattern candidates, blind-spot candidates (schema-validated) |
| `domain-model.md` | **v1.3** subject-specific concept map (standard/deep) |
| `calibration-report.md` / `calibration-summary.json` | Human + machine-readable audit summary |
| `calibration-trend-report.md` | Calibration improvement across sessions (deep mode) |
| `cross-model-validation.log.jsonl` | Real external reviewer verdicts (deep mode; `NOT_RUN` marker in the report when no reviewer is configured — never fabricated) |
| `dashboard.html` | Self-contained visual dashboard of the calibration data (inline SVG, offline) |

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
   Target: workspace | Stakes: medium

[PHASE] DEEP MODE: Standard + Cross-Model Validation + Trend Analysis

[PHASE] STANDARD MODE: Phase 0 -> 1 -> 2 -> 3 -> 4 -> 5 -> 6
  Phase 0: Mapping workspace...
    Found 0 source dirs, 2 candidate conventions
  Phase 1: Extracting assumptions...
    Extracted 7 assumptions
  Phase 2: Running calibration tests...
    [OK] ASSUME-007: CONFIRMED (delta: 0.30)
    [FAIL] ASSUME-003: FALSIFIED (delta: -0.85)
    [?] ASSUME-004: INCONCLUSIVE (delta: 0.00)
    [?] ASSUME-005: INCONCLUSIVE (delta: 0.00)
    [FAIL] ASSUME-006: FALSIFIED (delta: -0.85)
    [OK] ASSUME-001: CONFIRMED (delta: 0.07)
    [OK] ASSUME-002: CONFIRMED (delta: 0.05)
    Tested 7 assumptions (budget 50), skipped 0 known-false
  Phase 3: Mapping blind spots...
    Identified 2 blind spots (top 15), 0 recurring
  Phase 4: Synthesizing learning units...
    Created 2 learning units
  Phase 5: Updating knowledge base...
    [NEW] LU-001 -> VERIFIED (written to memory)
    [NEW] LU-002 -> VERIFIED (written to memory)
    Knowledge base: 2 new -> VERIFIED, 0 promoted, 0 PERSISTED (total: 2)
  Deep: Cross-model validation...
    NOT_RUN: no external reviewer command configured
  Deep: Historical trend analysis...
    Analyzed 7 calibration records
```

And the resulting **blind-spot register**:

```markdown
| Rank | ID     | Category            | Layer | Severity | Delta | Learning Unit |
|------|--------|---------------------|-------|----------|-------|---------------|
| 1    | BS-001 | CALIBRATION_ERROR   | L3    | Critical | -0.85 | LU-001        |
| 2    | BS-002 | CALIBRATION_ERROR   | L3    | Critical | -0.85 | LU-002        |

### BS-001 -- Critical L3 CALIBRATION_ERROR
- **Assumption**: Workspace follows Clean architecture layers (domain/app/infra)
- **Evidence**: Complete directory inventory shows no layer separation: docs/, evals/, skills/, templates/
```

Note what the output *refuses* to do: `ASSUME-004`/`ASSUME-005` stay `INCONCLUSIVE` because this repo's docs only *mention* monolith/microservice patterns in worked examples — prose is not behavior, so a keyword match never "confirms" a claim. Everything that is `CONFIRMED` or `FALSIFIED` is backed by a real observation made during the run.

Run it again and the **self-learning loop** kicks in — the falsified assumptions are remembered, not re-tested:

```text
    [MEMORY] 2 assumptions already FALSIFIED (skipping re-test)
    [SKIP] ASSUME-003: KNOWN FALSE (from prior sessions)
    [SKIP] ASSUME-006: KNOWN FALSE (from prior sessions)
    Tested 5 assumptions (budget 50), skipped 2 known-false
    ...
    Knowledge base: 0 new -> VERIFIED, 0 promoted, 4 PERSISTED (total: 0)
```

The corrections carried across sessions get promoted `VERIFIED → PERSISTED` (cross-session stable), and an assumption falsified 3+ times across sessions escalates to `PERSISTENT_BLIND_SPOT` with its learning unit marked `PERSISTED`. That continuity is the whole point.

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

**Core requirements:** Python 3.10+ and read/write access to the workspace's knowledge/memory roots (`.claude/` by default). That's it — the engine is dependency-free and harness-agnostic. The Claude Code plugin install additionally wants Claude Code v2.1.218+ (for `context: fork`, `background: true`).

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

# Also discover & calibrate what the user needs/intends/knows (user-context)
/self-audit --mode deep --user-context

# Audit a plan or a diff instead of the workspace (stakes set the budget)
/self-audit --target plan --stakes high "the plan text or a path"
/self-audit --target diff --stakes high

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
                         [--workspace WORKSPACE]
                         [--target {workspace,plan,diff,last-answer}]
                         [--stakes {low,medium,high}] [--output-dir OUTPUT_DIR]
                         [--no-cross-model] [--no-trend] [--user-context] [--verbose]
```

`--stakes` sets the verification budget and picks the default mode (`low→quick`, `medium→standard`, `high→deep`); an explicit `--mode` overrides it.

### Visualize the calibration data

Turn any audit's artifacts into a single self-contained HTML dashboard (inline SVG charts — calibration curve, blind-spot distribution, layer breakdown, trend — no external libraries, works offline):

```bash
python skills/self-audit/scripts/generate-dashboard.py --knowledge-root .claude/knowledge
# → .claude/knowledge/dashboard.html
```

---

## Configuration

Control the run through environment variables — this is what makes it portable across harnesses:

| Variable | Default | Description |
|----------|---------|-------------|
| `SELF_AUDIT_WORKSPACE` | `.` | Workspace root to audit |
| `SELF_AUDIT_KNOWLEDGE_ROOT` | `<workspace>/.claude/knowledge/` | Where artifacts are written |
| `SELF_AUDIT_MEMORY_ROOT` | `<workspace>/.claude/projects/<slug>/memory/` | Memory system root |
| `SELF_AUDIT_MODE` | `deep` | Default depth mode (`quick` / `standard` / `deep`) |
| `SELF_AUDIT_TARGET` | `workspace` | What is being audited (`workspace` / `plan` / `diff` / `last-answer`) |
| `SELF_AUDIT_STAKES` | `medium` | Verification budget (`low` / `medium` / `high`); sets default mode |
| `SELF_AUDIT_SESSION_ID` | auto (`session-YYYYMMDD-HHMMSS`) | Session id for trend grouping — set it to correlate runs across harnesses |
| `SELF_AUDIT_CROSS_MODEL` | `true` | Cross-model validation (deep mode) |
| `SELF_AUDIT_TREND_ANALYSIS` | `true` | Historical trend analysis (deep mode) |
| `SELF_AUDIT_VERBOSE` | `false` | Verbose logging (per-assumption evidence + blind-spot details) |
| `SELF_AUDIT_MAX_ASSUMPTIONS` | `0` (auto) | Cap assumptions tested (0 = mode default) |
| `SELF_AUDIT_QUICK_TOP_N` | `5` | Blind spots ranked in quick mode |
| `SELF_AUDIT_BLIND_SPOT_THRESHOLD` | `0.3` | Min \|confidence delta\| to escalate to a blind spot |
| `SELF_AUDIT_EXTERNAL_REVIEWERS` | unset | Real external reviewer commands (JSON list of `{name, command}`); unset = `NOT_RUN`, never fabricated |
| `SELF_AUDIT_TREND_MIN_SESSIONS` | `2` | Min sessions before trend direction is computed |
| `SELF_AUDIT_USER_CONTEXT` | `false` | Also discover & calibrate user-context assumptions (intent, needs, tacit knowledge, goal-task fit) |

---

## Works beyond Claude Code

The **epistemic engine is plain Python + Markdown/JSONL**, so it runs anywhere an agent can execute a script and read/write files — no account, no API key, no vendor runtime:

- **Claude Code** — as a native skill (`/self-audit`), with memory + skill integration
- **CLI / TUI agents** — Codex, Gemini CLI, OpenCode, Aider, Hermes, and any shell-driven agent: invoke `run-self-audit.py` directly
- **IDE agents & extensions** — VS Code (Copilot, Cline, Roo, Continue), JetBrains AI Assistant, Zed, Cursor: run the script from the integrated terminal or an agent task, and point the agent at `SKILL.md` as its instructions
- **Desktop agent apps** — any desktop harness that can run Python and read/write a workspace (the artifacts are plain Markdown/JSONL you can open anywhere)
- **CI** — run the audit on a schedule and diff the blind-spot map between runs
- **Humans** — the scripts are plain `python script.py` with zero third-party dependencies; `generate-dashboard.py` renders the results as one offline HTML file

The `SKILL.md` body works as a paste-in system prompt or agent instruction file in any harness; the YAML frontmatter is Claude Code plugin metadata (ignored elsewhere). No `ANTHROPIC_API_KEY` required. No LLM judge required for evals — the graders are static.

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
│       ├── generate-dashboard.py    # Self-contained HTML dashboard
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