---
name: self-audit
description: Surfaces candidate unknowns and blind spots in a workspace — what the model doesn't know it doesn't know, AND what the user needs/knows/doesn't-know even when they can't articulate it — before implementation, review, or release. Use when asked to self-audit, run a calibration check, find blind spots, or answer "what am I missing?" / "what don't you know about this repo?", or before acting on high-stakes conclusions about a workspace. Runs structured epistemic calibration: extracts implicit assumptions (model + user), tests them against real evidence, maps blind spots by abstraction layer (L1-L4), synthesizes learnable units with verification protocols, persists calibrated knowledge to project memory. Read-only by default: writes only to knowledge/memory roots.
when_to_use: "Starting a new session in a workspace; before major implementation or release; when asked 'what am I missing' or 'what don't you know about this repo'; when repeatedly surprised by same workspace patterns; when cross-session learning keeps resetting; when you need to audit your own knowledge boundaries before claiming expertise; when user intent is vague but workspace has strong implicit constraints; when user says 'I know what I want' but requirements keep shifting"
argument-hint: "[--mode quick|standard|deep] [--workspace PATH] [--target workspace|plan|diff|last-answer] [--stakes low|medium|high] [--output-dir PATH] [--user-context]"
arguments: "mode workspace target stakes output-dir user-context"
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
  tags: ["epistemic-calibration", "workspace-analysis", "knowledge-discovery", "blind-spot-detection", "user-intent-modeling", "tacit-knowledge-extraction"]
  version: "1.2.0"
  min-claude-version: "2.1.218"
license: MIT
compatibility: "Requires Python 3.10+, pytest, read/write access to .claude/ directory. Works on any workspace with code/docs/tests."
---

# Self-Audit — Epistemic Calibration & Workspace Knowledge Discovery

## Overview

Most AI failures aren't reasoning errors — they're **calibration errors**. The model confidently assumes a pattern holds, a convention exists, or a library behaves a certain way, but the workspace reality differs. **Equally critical**: the user often cannot fully articulate what they need, what they know, or what constraints exist — yet the workspace encodes all of this implicitly.

This skill performs **dual calibration**:
1. **Model calibration**: What the model assumes vs. what's actually true in the workspace
2. **User context calibration**: What the user needs/intends/knows (even unarticulated) vs. what the workspace actually requires/constrains

**Objective:** Transform "I thought X was true" into "X is false (confirmed), here's the evidence, here's the corrected pattern, and here's the memory artifact so I don't relearn it." AND transform "User said Y" into "User actually needs Z (inferred from workspace constraints, tacit patterns, and goal-task gaps), here's the verification protocol."

This is not `universal-brainstorming` (topic-driven discovery) nor `doubt-driven-development` (decision-stress-testing). This is **continuous epistemic hygiene** for the model-workspace-user interface.

**Honesty bound:** This audit does not claim to discover every unknown or infer certainty from a lack of evidence — it surfaces candidate blind spots bounded to the inspected scope.

## Non-Negotiables (the whole skill in ten lines)

1. **Evidence over memory** — FACT only from this session's tool output; everything else is a labeled belief (§1)
2. **Absence of evidence ≠ evidence of absence** — a null search confirms nothing beyond its stated scope (§4)
3. **Verify, don't just list** — run the cheapest check that could decisively falsify the claim (§4)
4. **Disconfirm first** — attack the current picture; a confirm-only probe is not a probe (§4)
5. **Read-only workspace** — writes go only to knowledge/memory roots; fix mode only on explicit request (Fix Mode & Write Policy)
6. **Never fabricate** — an empty field is honest, a filled invention is fabrication (Anti-Pattern #11)
7. **Speculation is not a defect** — label it; never phrase it as a confirmed problem (Anti-Pattern #19)
8. **Stakes set the budget** — but every load-bearing claim gets checked regardless of mode (§7)
9. **"Not found" means "not found in scope"** — never "doesn't exist" (§4)
10. **Stop explicitly** — name what remains unknown and out of scope; never imply completeness (Stop Conditions)

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
| **FACT** | Directly verified by workspace evidence **produced in this session's tool output** (test run, grep, file read) | "pytest runs with `python -m pytest`" (verified by running) |
| **WORKSPACE_CONVENTION** | Pattern observed repeatedly in this workspace, not universal | "All handlers use `Result<T, E>` return type" (seen in 12 files) |
| **ASSUMED_FACT** | Model believed true without verification; confidence stated explicitly | "This function returns None on error" (confidence: 0.8) |
| **UNVERIFIED_PATTERN** | Pattern inferred but not systematically checked | "All async functions use `await` correctly" (not grep-verified) |
| **IMPLICIT_CONVENTION** | Unwritten rule discovered via deviation analysis | "Config keys use SCREAMING_SNAKE_CASE" (inferred from 8/10 files) |
| **DOMAIN_GAP** | Missing domain knowledge the workspace assumes | "Songs use verse-chorus structure" (requires domain docs) |
| **CALIBRATION_ERROR** | Confidence ≠ accuracy discovered via test | "Thought `config.get()` raises KeyError; actually returns None" |
| **SPECULATION** | Plausible but insufficient evidence | "This module might be deprecated" (no deprecation marker found) |

**Evidence cutoff:** FACT (and same-session `WORKSPACE_CONVENTION`) require observation **in this session's tool output**. Claims loaded from memory files, prior calibration logs, or earlier conversations enter as `ASSUMED_FACT` with `verified_this_session: false` and are re-verified in Phase 2 before any upgrade — a memory read this session is evidence of what the memory *says*, not of the workspace fact. Prior-session reads and model memory never qualify.

**Provenance:** every claim also carries `provenance: OBSERVED_THIS_SESSION | INFERRED | RECALLED | ASSUMED` (the claim's origin; the statuses above stay canonical and are never renamed). Observed ≈ FACT; Inferred ≈ UNVERIFIED_PATTERN (requires a `reasoning_chain`); Recalled ≈ belief from training memory, unchecked against this workspace; Assumed ≈ ASSUMED_FACT. **Recalled and Assumed are the audit targets.**

**Rule:** Never upgrade a status because it "feels right" — confidence must never increase from repetition alone. Equally, never downgrade a verified fact out of reflexive caution: confidence tracks evidence in both directions. Soft qualifiers ("probably", "likely") never substitute for a labeled entry — a guess carries a status and a band, not a hedge word.

### 2. Confidence Scale — Explicit and Quantitative

Every `ASSUMED_FACT` and `UNVERIFIED_PATTERN` carries a confidence score (0.0–1.0):

- **0.9–1.0**: Would bet significant resources on it
- **0.7–0.89**: Reasonable working assumption, needs verification before committing
- **0.5–0.69**: Weak signal, treat as hypothesis
- **0.3–0.49**: Leaning against, but not ruled out
- **0.0–0.29**: Strongly doubt, but not falsified

Confidence is the **model's internal probability estimate**, not a rhetorical device. Numbers are legitimate here because they are *measured*: `confidence_delta` scores stated confidence against actual outcomes in the calibration log. **Measurement split:** numeric confidence goes only on claims that enter `CALIBRATION_LOG.jsonl`; anything without a calibration entry (SPECULATION, POSSIBLE_BLIND_SPOT, untested DOMAIN_GAP) carries the qualitative band **HIGH/MEDIUM/LOW** instead. Decorative unmeasured numbers stay banned (Anti-Pattern #6).

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
3. **Document & test cross-reference** — Compare docstrings/README/ADR vs implementation **vs test assertions** — all three legs; flag any pair that agrees while the third diverges
4. **Memory/ADR cross-check** — Compare against persisted memory decisions; can corroborate or contradict, but yields only a labeled belief (`ASSUMED_FACT` / `MEMORY_DRIFT` finding) — **never FACT** (§1 evidence cutoff)
5. **Expert/human query** — Only when automated verification impossible

**Cheapest decisive check:** for each claim, run the cheapest check capable of decisively falsifying it — the claim's `falsifier` defines it (grep the symbol before running the suite; open the one file before scanning the tree). A check that cannot return FALSIFIED (re-reading your own reasoning or the doc the belief came from) is not a verification.

**Disconfirmation preference:** prefer the check most likely to prove the current picture WRONG — probe where error is most likely (L3/L4, USER_*, high-confidence claims), never gather ceremonial confirming samples.

**Observation is a closed set:** only these acts count — reading file content, executing a command, receiving tool output. Directory listings, filenames, and familiarity are not observation.

**Negative results:** "searched and found nothing" is evidence only with a stated scope — `search_scope: {paths, ignore_rules, case_sensitive, file_types}`. "Not found" means "not found under scope S", never "does not exist". A search-based test that cannot state its scope up front is **not CONFIRMED-capable**: it runs as `INCONCLUSIVE`/`check_status: BLOCKED`. A null counterexample search never produces automatic FACT at 1.0 — with a complete bounded scope it is `CONFIRMED` worded "no counterexamples in <scope>" capped at `WORKSPACE_CONVENTION`; scope is always part of the claim.

**Behavior outranks prose:** comments, READMEs, ADRs, and commit messages are claims to verify, not evidence of behavior. When prose and code disagree, the code is the FACT and the discrepancy is recorded as a finding with `finding_kind: DOC_DRIFT` (an ordinary record — no special status value).

**Version suspicion:** any version number, version-like name, or fast-moving library API is suspect until verified against this workspace's pinned manifest/lockfile/API surface — memory is the unreliable side of that comparison. Before invoking a command, flag, or API in a check, confirm it exists in the pinned version (`--help`, docs, dry run); failure of an unconfirmed invocation is not project evidence.

**Probe safety:** probes never delete, overwrite, or reset workspace state (mutating tests run sandboxed or are logged `check_status: BLOCKED`); no deploys, remote pushes, ticket writes, or mutating API calls; never open env files, key stores, or credential-bearing config — record their existence only. A missing tool is an environment constraint, never project evidence.

"Seems right" is never sufficient.

### 5. Calibration Data Persists Across Sessions

The calibration log (confidence vs. actual accuracy) is **append-only and persistent**. It builds a model self-awareness profile over time:
- Systematic overconfidence regions (e.g., "I always overestimate my knowledge of test conventions")
- Systematic underconfidence regions
- Domain-specific calibration curves

This data lives in `.claude/knowledge/calibration.log.jsonl` and is loaded at session start. **Loaded ≠ observed:** everything read back from memory or prior logs enters as a belief with `verified_this_session: false` (§1) and only re-observation upgrades it.

### 6. Workspace Knowledge ≠ Universal Truth

A convention discovered in this workspace (e.g., "all handlers return `Result`") is **workspace knowledge**, not a universal best practice. Label it `WORKSPACE_CONVENTION` with `scope: "this-project"`. Do not generalize to other projects without explicit cross-project validation.

### 7. Scope, Stakes & Target — Two Lines Before Anything Else

Before Phase 0 inventory, state in **exactly two lines**: (1) **what is being audited** — one of `workspace | plan | diff | last-answer`; never silently default to the repo — and (2) **which decision depends on the result** (e.g. "whether to proceed with the auth refactor"). Plan/diff content comes as argument text or a path; `last-answer` means the invoking session's preceding assistant turn (and `USER_CONFIRMED` likewise needs live conversation) — in a `context: fork` background run these default to `--target workspace`.

**Stakes set the verification budget:** `--stakes low|medium|high` (default medium). Low = spot checks sufficient to confirm or falsify the load-bearing claim (a ceiling, not an excuse for zero verification); high = **stakes cap wins**: every load-bearing claim is checked before stopping regardless of mode or top-N budget. Stakes choose how much the decision can afford to be wrong; mode chooses how much trivia to cover. Default mode follows stakes (low→quick, medium→standard, high→deep); an explicit `--mode` overrides.

## Depth Modes

**One budget rule (canonical):** Phase 2 tests the **top N by risk** of the register (N = quick 10 / standard 25 / deep 50, overridable via `SELF_AUDIT_QUICK_TOP_N` / `SELF_AUDIT_MAX_ASSUMPTIONS`) **plus every load-bearing claim** — load-bearing first. Untested assumptions keep their honest status and still get log entries. The pre-mortem's three checks count toward N.

### Quick (~5–10 min)
`Phase 0 → Phase 1 (top 20 assumptions) → Phase 2 (top 10 by risk + load-bearing) → Phase 3 → Pre-Mortem (short) → Phase 6`
Output: `BLIND_SPOT_REGISTER` (top 5), `CALIBRATION_REPORT` (minimum: Bottom Line + Top Blind Spots + Stop Reason + Open Questions)

### Standard (~20–30 min)
Full Phase 0–6 workflow. All assumptions extracted; top 25 by risk + all load-bearing verified; all blind spots mapped; learning units synthesized.
Output: Full artifact suite.

### Deep (default) (~45–60+ min)
Standard (top 50) + **Pre-Mortem Protocol** (extended) + **Cross-Model Validation** (fresh-context adversarial reviewer per `doubt-driven-development`) + **Historical Trend Analysis** (load calibration.log, compute drift, flag recurring miscalibration patterns).
**Sequencing:** cross-model reviewers receive the post-Phase-2 corrected picture and attack residual risk — but may dispute any Phase 2 verdict (disagreement logs as `CONTRADICTION`, Anti-Pattern #10).
Output: Full artifact suite + `CROSS_MODEL_VALIDATION.log` + `CALIBRATION_TREND_REPORT`.

Default: **deep** for high-stakes work; per §7 the default follows `--stakes`, and `--mode` overrides explicitly. Low stakes may cap or skip the deep-only extensions (cross-model, trend) even in deep mode.

## Workflow (Phase-Based)

**Ordering invariant:** no Phase 2 probe may target a surface Phase 0 did not map and Phase 1 did not register. A surface that was mapped but never registered appears in the Coverage Ledger as `Never-touched` — never silently absent.

### Phase 0 — WORKSPACE MAP (Passive Scan)

**Goal:** Build a read-only model of the workspace — what exists, how it's organized, what conventions are visible.

**Inputs:** Workspace root path (default: `${CLAUDE_PROJECT_DIR}`); the §7 two-line scope statement (recorded as `audit_purpose` + `relevant_areas`)

**Actions** (full per-action checklists in `reference.md`):
1. **Record scope** — persist the §7 statement as `target`, `audit_purpose`, `decision_dependency`, `relevant_areas`; everything outside `relevant_areas` becomes an explicit scope limit
2. **Inventory & scope limits** — source/test/config/doc/memory dirs; entry-point docs (README, CONTRIBUTING, CLAUDE.md, AGENTS.md, Makefile, scripts, CI config, Dockerfile, `.env.example`); record generated/ignored/unexamined areas as scope limits
3. **Stack & manifests** — languages, frameworks, build tools, test runners; pinned versions from manifests/lockfiles; note which expected tools actually exist (missing tool = environment constraint, §4)
4. **Repository status** — git status, branch, recent log
5. **System traces** — entry points, dependency edges, data flows, configuration effects, test assertions (what behavior the tests actually pin)
6. **Hidden-state sweep** — untracked/ignored files, submodules, vendored code, monorepo workspaces, generated files that look hand-written
7. **Environment audit** — OS, runtime versions, network constraints, required services; required secrets by **existence only** (never open env files or key stores — §4 probe safety)
8. **Convention sampling + debt markers** — 5–10 high-signal greps per detected stack (naming, error handling, async, config, logging, DI) + TODO/FIXME/XXX/HACK, deprecated, skipped/disabled tests
9. **Test checklist** — do tests exist; how are they run; do they pass right now; what do they not cover; does any doc claim behavior no test pins
10. **Memory load** — `MEMORY.md` + memory files, ADRs, CLAUDE.md/AGENTS.md instructions; extract candidate implicit rules (frequency ≥ 3 occurrences, ≤ 2 exceptions) — loaded material stays a belief (§5)
11. **Coverage ledger** — classify every directory/file as `Opened | Seen-only | Never-touched`, plus a command ledger of commands actually run vs. commands merely assumed to behave a certain way (canonical home: `WORKSPACE_MODEL.json.coverage_ledger`)

**Output:** `WORKSPACE_MODEL.md` + `WORKSPACE_MODEL.json`

**Epistemic Status:** All conventions here are `UNVERIFIED_PATTERN` until Phase 2 verifies. If the workspace is empty or tiny, say so plainly and stop early (STOP F).

---

### Phase 0.5 — USER CONTEXT DISCOVERY (Tacit Knowledge & Intent Modeling)

**Goal:** Discover what the user *needs*, *knows*, *assumes*, and *cannot articulate* about the workspace — by analyzing the workspace itself as a crystallization of user intent, constraints, and domain expertise.

**Rationale:** The workspace is not just code — it's a fossil record of user decisions, constraints, domain knowledge, and implicit requirements. Even when users can't articulate "I need X" or "I assume Y", the workspace structure, naming, conventions, test patterns, config choices, and documentation gaps reveal the user's true mental model and unspoken needs.

**Inputs:** 
- `WORKSPACE_MODEL` (from Phase 0)
- User's explicit statements (if any) from conversation history
- `.claude/` memory files, CLAUDE.md, AGENTS.md
- Git history (commit messages, branch names, PR titles)
- Issue tracker / TODO comments / README intent statements

**Prose is not behavior:** commit messages, branch names, PR titles, and issue text are claims about intent and history — evidence of what was *said*, never of what the code *does* (§4 behavior outranks prose). Use them to generate assumptions; when they describe code that has moved on, record `finding_kind: STALE_BASIS`.

**Actions:**

1. **User Intent Reconstruction** — Reverse-engineer user goals from workspace artifacts:
   - **Architectural intent**: What problem is this architecture solving? (e.g., "modular monolith" → user values deployability + domain isolation)
   - **Convention intent**: Why this naming/error/config pattern? (e.g., `Result<T,E>` everywhere → user prioritizes explicit error handling)
   - **Test intent**: What behaviors are being protected? (e.g., contract tests → user cares about API stability)
   - **Config intent**: What environments/deployments are targeted? (e.g., YAML + env vars → user does multi-env deployments)

2. **User Knowledge Mapping** — Infer what the user *knows* vs. *assumes*:
   - **Explicit knowledge**: Documented in ADRs, README, CLAUDE.md, code comments
   - **Tacit knowledge**: Encoded in consistent patterns without documentation (e.g., all services use DI but no ADR says so)
   - **Assumed knowledge**: Patterns user expects but aren't enforced (e.g., "everyone knows we use snake_case for DB columns")
   - **Blind knowledge**: Things user *doesn't know* the workspace does (legacy patterns, deprecated paths, implicit couplings)

3. **User Need Gap Analysis** — Identify what the user *needs* but hasn't expressed:
   - **Constraint gaps**: Workspace has implicit constraints user ignores (e.g., "services must be stateless" but user adds session state)
   - **Capability gaps**: Workspace lacks capability user implicitly assumes (e.g., user assumes "async everywhere" but sync calls exist)
   - **Evolution gaps**: Workspace evolved past user's mental model (e.g., user thinks "clean architecture" but code is modular monolith)
   - **Integration gaps**: User wants X but workspace requires Y (e.g., user wants GraphQL but REST contracts are hardcoded)

4. **Goal-Task Misalignment Detection** — Compare user's stated goals vs. workspace reality:
   - Parse explicit user statements: "I want to refactor auth", "Add feature X", "Make it faster"
   - Map to workspace constraints: auth module has 50% test coverage, circular deps, no interfaces
   - Flag mismatches: "User wants quick refactor → workspace requires 3-week stabilization first"

5. **Tacit Requirement Extraction** — Find requirements the user never stated but workspace enforces:
   - **Implicit invariants**: "No direct DB access in handlers" (enforced by convention, not linting)
   - **Domain rules**: "All prices in cents" (encoded in types, not documented)
   - **Security boundaries**: "PII never leaves service boundary" (enforced by architecture)
   - **Performance budgets**: "p99 < 200ms" (encoded in test thresholds)

**Output:** `USER_CONTEXT_MODEL.md` + `USER_CONTEXT_MODEL.json`

```json
{
  "reconstructed_intent": [
    {"aspect": "architecture", "intent": "modular monolith for deployability + domain isolation", "confidence": 0.85, "evidence": ["core/ imports runtime/", "no domain/app/infra dirs"]},
    {"aspect": "error_handling", "intent": "explicit error handling via Result<T,E>", "confidence": 0.9, "evidence": ["30 files use Result", "2 use try/catch"]}
  ],
  "user_knowledge_map": {
    "explicit": ["ADR-001: modular monolith", "README: testing strategy"],
    "tacit": ["DI pattern in 12 services", "snake_case for DB columns"],
    "assumed": ["async everywhere", "no circular deps"],
    "blind": ["legacy sync calls in payments/", "deprecated v1 API still active"]
  },
  "need_gaps": [
    {"gap": "constraint_gap", "description": "User adds session state but workspace assumes stateless services", "severity": "High", "layer": "L3"},
    {"gap": "capability_gap", "description": "User assumes async everywhere; sync REST calls exist", "severity": "Critical", "layer": "L3"},
    {"gap": "evolution_gap", "description": "User mental model: clean architecture; actual: modular monolith", "severity": "Critical", "layer": "L3"},
    {"gap": "integration_gap", "description": "User wants GraphQL; workspace has hardcoded REST contracts", "severity": "Medium", "layer": "L2"}
  ],
  "goal_task_misalignments": [
    {"user_goal": "quick auth refactor", "workspace_reality": "auth has 50% test coverage, circular deps, no interfaces", "estimated_effort_multiplier": 5, "risk": "High"}
  ],
  "tacit_requirements": [
    {"requirement": "stateless_services", "evidence": "all services use DI, no singleton state", "enforcement": "convention", "falsifier": "find service with mutable instance state"},
    {"requirement": "prices_in_cents", "evidence": "Money type used in 40 files, never float", "enforcement": "type_system", "falsifier": "find float price calculation"}
  ]
}
```

**Epistemic Status:** All findings here carry `USER_INFERRED` status — they are hypotheses about user mental state, not verified facts. They must be validated via Phase 2 calibration tests or explicit user confirmation.

---

### Phase 1 — CLAIM & ASSUMPTION CAPTURE (Active Probe — Model + User)

**Goal:** From the workspace model AND user context model, capture **both** the model's implicit assumptions AND the user's implicit assumptions/needs — things the model/user "know" but haven't verified. Capture every substantive claim **already made or about to be made** (architecture, build/run, module behavior, test coverage, dependency API, domain rules, user model) — a prospective claim the next step would silently rely on is still a claim.

**Input:** `WORKSPACE_MODEL` + `USER_CONTEXT_MODEL` + model's internal knowledge

**Process:** For each convention, pattern, structural element, AND user intent/need/tacit requirement, generate assumption candidates:

| Assumption Type | Template | Example |
|-----------------|----------|---------|
| **Convention** | "All X follow pattern Y" | "All config files use YAML" |
| **Behavioral** | "Function/module X does Y when Z" | "`generate()` returns a song object" |
| **Invariant** | "Condition X never occurs" | "No raw SQL in core module" |
| **Delegation** | "Library/tool X handles Y" | "pytest-asyncio handles all async test cases" |
| **Architectural** | "System follows pattern X" | "Workspace uses clean architecture layers" |
| **Domain** | "Domain rule X applies" | "All Turkish pop songs use 126 BPM" |
| **USER_INTENT** | "User intends X based on workspace pattern Y" | "User intends explicit error handling via Result<T,E>" |
| **USER_NEED** | "User needs X but workspace constrains Y" | "User needs async everywhere but sync calls exist" |
| **USER_TACIT** | "User tacitly assumes X (encoded in workspace)" | "User assumes prices always in cents" |
| **USER_BLIND** | "User is unaware of X in workspace" | "User unaware of legacy sync calls in payments/" |

**For each assumption, ask the five probe questions** and store the answers as fields (the questions are the discipline; the fields are their record):

| Probe question | Field |
|----------------|-------|
| What must be true for this conclusion to hold? | `preconditions` |
| What evidence supports it? | `source_evidence` |
| What evidence would disconfirm it? | `falsifier` |
| Which edge cases or paths are unexamined? | `edge_cases_unexamined` |
| Could a similar name, config, or code path refer to something different? | `possible_confusions` |

**For each assumption, record:**
```json
{
  "id": "ASSUME-001",
  "type": "CONVENTION|BEHAVIORAL|INVARIANT|DELEGATION|ARCHITECTURAL|DOMAIN|USER_INTENT|USER_NEED|USER_TACIT|USER_BLIND",
  "claim_kind": "architecture|build_run|module_behavior|test_coverage|dependency_api|domain_rule|user_model",
  "statement": "All config files use YAML",
  "source_evidence": "WORKSPACE_MODEL.conventions[0] (frequency 8)",
  "confidence": 0.85,
  "testable": true,
  "layer": "L2",
  "scope": "workspace",
  "falsifier": "Find a non-YAML config file in active use",
  "preconditions": ["sampled configs are the active ones", "no generated-only config dirs"],
  "edge_cases_unexamined": ["runtime/ generated configs"],
  "possible_confusions": ["config.json may be an example file, not active config"],
  "epistemic_status": "ASSUMED_FACT|USER_INFERRED"
}
```

**Verification priority:** score each claim `impact × (1 − confidence)` where impact = 3 (decision-blocking) / 2 (significant) / 1 (minor); sort descending. Phase 2 tests the top N by this score **plus every load-bearing claim** (Depth Modes budget rule); under `--stakes high` the load-bearing set is checked in full regardless of budget (stakes-cap-wins, §7).

**Output:** `ASSUMPTION_REGISTER.json` (array of assumption objects)

**Target:** 40–150 assumptions per workspace (deep mode). Prioritize L2/L3/L4 + USER_* types.

---

### Phase 2 — CALIBRATION TESTS (Verification — Model + User Assumptions)

**Goal:** Test `testable=true` assumptions (both model and user-derived) against workspace evidence — within the Depth Modes budget (top N by risk + all load-bearing; `--stakes high` checks all load-bearing regardless).

**Design rules:** (a) run the **cheapest decisive check** — the one the claim's `falsifier` defines; a check that cannot return FALSIFIED is not a verification (§4). (b) **Disconfirm first** — probe where the current picture is most likely wrong, never gather ceremonial confirming samples (§4). (c) A search-based test states its `search_scope` up front or runs `INCONCLUSIVE` / `check_status: BLOCKED` (§4 negative results).

**For each assumption in `ASSUMPTION_REGISTER` (budgeted):**

1. **Design test** — Minimal verification step per type:
   - `CONVENTION` → `rg`/`grep` pattern search across relevant files
   - `BEHAVIORAL` → Run function/test, inspect return value/side effects
   - `INVARIANT` → Search for counterexamples (grep for anti-pattern)
   - `DELEGATION` → Check library docs / run minimal integration test
   - `ARCHITECTURAL` → Check import graph, directory structure, ADRs
   - `DOMAIN` → Cross-reference with domain docs, memory, examples
   - `USER_INTENT` → Verify intent hypothesis against workspace patterns (e.g., "User intends explicit error handling" → count Result<T,E> vs try/catch)
   - `USER_NEED` → Test gap hypothesis (e.g., "User needs async everywhere" → search for sync calls in async contexts)
   - `USER_TACIT` → Verify tacit requirement enforcement (e.g., "User assumes prices in cents" → type-check Money usage vs float)
   - `USER_BLIND` → Verify blind spot existence (e.g., "User unaware of legacy sync calls" → search for deprecated patterns)

2. **Execute test** — Record (every field; an empty field is honest, an invented one is fabrication — Anti-Pattern #11):
   - `prediction`: What model/user expected (from assumption statement)
   - `actual`: What test observed
   - `evidence`: File paths, command output, line numbers — only what the tool actually returned
   - `verification_method`: which §4 method ran (`code_execution` | `static_analysis` | `doc_test_crossref` | `memory_crosscheck` | `expert_query`)
   - `session_id`, `timestamp`
   - `search_scope` (any search-based test), `commands_ran`, `commands_assumed`
   - `check_status`: `RAN | BLOCKED | SKIPPED` — for `BLOCKED` also `block_reason` + `unblock_condition`
   - `confidence_delta`: `actual_confidence - stated_confidence` (where actual_confidence = 1.0 if confirmed, 0.0 if falsified, 0.5 if inconclusive)
   - `assumption_origin`: `model` | `user_inferred`

3. **Classify result** (canonical values — never renamed):
   - `CONFIRMED` → `FACT` (positive observation) or `WORKSPACE_CONVENTION` or `USER_INTENT_VALIDATED` (confidence → 1.0). **Null-cap:** a CONFIRMED earned by a counterexample *search* is worded "no counterexamples in <scope>" and capped at `WORKSPACE_CONVENTION` — never automatic FACT at 1.0 (§4).
   - `FALSIFIED` → `CALIBRATION_ERROR` (model) or `USER_MISALIGNMENT` (user) — record delta and `corrected_belief` (what the truth is); the original prediction is retained in the log and in the learning unit's Current Belief, never overwritten.
   - `INCONCLUSIVE` → `UNVERIFIED_PATTERN` (confidence unchanged) + `inconclusive_reason`. A blocked check logs with `check_status: BLOCKED` and `result: INCONCLUSIVE` — BLOCKED is a check status, **never** a result value.
   - `USER_CONFIRMED` → User explicitly validated (live conversation).

4. **Update the working picture immediately** when a check corrects a belief — Phase 3, cross-model review, and the report all work from the corrected picture. Re-stating a superseded conclusion later is `finding_kind: STALE_BASIS` (Anti-Pattern #18).

**Output:** `CALIBRATION_LOG.jsonl` (append-one-per-assumption, including untested ones — their status stays honest)
```jsonl
{"assumption_id": "ASSUME-001", "session_id": "uuid", "timestamp": "2026-10-22T10:30:00Z", "prediction": "All configs YAML", "actual": "Found 2 JSON configs in runtime/", "evidence": ["runtime/config.json", "runtime/defaults.json"], "verification_method": "static_analysis", "search_scope": {"paths": ["**/config*"], "ignore_rules": "default", "case_sensitive": true, "file_types": [".yaml", ".yml", ".json"]}, "commands_ran": ["rg --files -g '*config*'"], "commands_assumed": [], "check_status": "RAN", "result": "FALSIFIED", "confidence_delta": -0.85, "corrected_belief": "configs are mixed: YAML at repo root, JSON under runtime/", "new_status": "CALIBRATION_ERROR", "layer": "L2", "assumption_origin": "model"}
{"assumption_id": "ASSUME-047", "session_id": "uuid", "timestamp": "2026-10-22T10:31:00Z", "prediction": "User intends explicit error handling via Result<T,E>", "actual": "30 files use Result<T,E>, 2 use try/catch, 3 use exceptions", "evidence": ["src/handler1.py", "src/handler2.py"], "verification_method": "static_analysis", "search_scope": {"paths": ["src/"], "ignore_rules": "default", "case_sensitive": true, "file_types": [".py"]}, "commands_ran": ["rg 'Result<' src/", "rg 'try:' src/"], "commands_assumed": [], "check_status": "RAN", "result": "CONFIRMED", "confidence_delta": 0.05, "new_status": "USER_INTENT_VALIDATED", "layer": "L2", "assumption_origin": "user_inferred"}
```
(Worked examples of a scoped-null CONFIRMED and a `BLOCKED` check are in `reference.md`.)

**Rule:** Every testable assumption MUST produce a log entry — tested or not (`check_status: SKIPPED` with a reason for budget/scope skips). No silent skips.

---

### Phase 3 — BLIND SPOT MAP (Gap Discovery — Model + User)

**Goal:** From calibration results, identify and classify blind spots by layer and severity for both model and user.

**Blind Spot Categories (Model):**

| Category | Definition | Severity |
|----------|------------|----------|
| **CALIBRATION_ERROR** | High confidence model assumption falsified | Critical if L3/L4, High if L2, Medium if L1 |
| **UNVERIFIED_CRITICAL** | `testable=true` but test inconclusive, layer L3/L4 | High |
| **IMPLICIT_CONVENTION_GAP** | Pattern exists but undocumented, deviation found | Medium |
| **DOMAIN_GAP** | Missing domain knowledge required by workspace | High if blocks task |
| **MEMORY_DRIFT** | Workspace changed since last memory write | Medium |
| **POSSIBLE_BLIND_SPOT** | Plausible gap not yet established (per UBS rule) | Low, discoverability: Hard |

**Blind Spot Categories (User):**

| Category | Definition | Severity |
|----------|------------|----------|
| **USER_MISALIGNMENT** | User's mental model contradicts workspace reality (falsified USER_INTENT/USER_NEED) | Critical if L3/L4, High if L2 |
| **USER_TACIT_GAP** | User tacitly assumes X but workspace doesn't enforce/contradicts | High |
| **USER_BLIND_SPOT** | User unaware of X in workspace (validated USER_BLIND) | High if L3/L4 |
| **USER_GOAL_TASK_MISMATCH** | User's stated goal incompatible with workspace constraints | Critical |
| **USER_IMPLICIT_CONSTRAINT_VIOLATION** | User ignores constraint workspace implicitly enforces | High |
| **USER_UNSTATED_REQUIREMENT** | Workspace requires X but user never mentioned it | Medium |

**Failure-Mode Scan** — before ranking, sweep the session's own reasoning for the standard failure modes (each maps to an anti-pattern or §4 rule; skip items that don't apply):
1. Treating a filename as evidence of its contents (Anti-Pattern #15)
2. Extrapolating from a sample to the whole (Anti-Pattern #7)
3. Trusting comments, READMEs, or commit messages over behavior (§4 behavior outranks prose)
4. Assuming a command, flag, or API exists in this version (Anti-Pattern #16)
5. Assuming tests pass or the build works without running it (Anti-Pattern #2)
6. Conflating "not found" with "doesn't exist" (§4 negative results)
7. Session drift: restating earlier conclusions without rechecking (Anti-Pattern #18)

**Blind Area Ranking** — rank every `Never-touched` Coverage Ledger item **ordinally** by how likely it is to contradict the current picture (most likely first). The top of this ranking seeds the report's Not-Yet-Examined bucket; the ranking is a suspicion order, never a finding.

**For each blind spot, produce** (worked examples per category in `reference.md`):

```markdown
### BLIND_SPOT-<NNN> (<Model|User>: <CATEGORY>)
- **Category**: <from the tables above>
- **Layer**: <L1–L4> · **Severity**: <Critical|High|Medium|Low> · **risk**: severity × layer_weight (L4=4 … L1=1)
- **Claim**: <the assumption / user assumption / tacit assumption — per category>
- **Premises**: <what must be true for this claim to hold — the `preconditions` carried from Phase 1>
- **Evidence**: <file paths, command output, line numbers — or "none yet">
- **Confidence Delta**: <signed delta — only for claims with calibration-log entries> | **Likelihood**: <HIGH|MEDIUM|LOW> (unmeasured claims, §2)
- **Unexamined Paths**: <edge cases and paths never touched — `edge_cases_unexamined`>
- **Discoverability**: <Easy|Moderate|Hard> · **Impact**: <what breaks if the picture is wrong>
- **Smallest Useful Check**: <the single cheapest probe that could settle it>
- **Learning Objective**: <what to learn or correct>
- **Verification Protocol**: <decisive checks>
- **Integration Point**: <which skills to tag>
```

(Worked examples for the user categories — `USER_MISALIGNMENT`, `USER_TACIT_GAP`, `USER_GOAL_TASK_MISMATCH` — are in `reference.md`.)

**Output:** `BLIND_SPOT_REGISTER.md` (markdown table + detail sections for both model and user blind spots)

**Stop Condition for Quick Mode:** Top 5 blind spots by (severity × layer_weight) where L4=4, L3=3, L2=2, L1=1. Includes both model and user categories.

---

### Pre-Mortem Protocol (all modes)

**Prompt:** "If a maintainer who knows this repo well reviewed my conclusions, what **three** things would they say I got wrong or missed?" Exactly three items — no more, no less, no padding (Anti-Pattern #14). For each item: name it, then run **one decisive check** aimed at it. Register each pre-mortem claim before checking it — the ordering invariant applies. Findings enter the register and blind-spot map like any other; update the picture immediately.

- **Quick / Standard:** the three items + three checks, done (short form in quick).
- **Deep (extended):** additionally hand the three items to a fresh-context cross-model reviewer to attack; disagreements log as `CONTRADICTION` (Anti-Pattern #10).
- The three checks count toward the Phase 2 budget (Depth Modes).

Full protocol and worked examples in `reference.md`.

---

### Phase 4 — LEARNABLE UNIT SYNTHESIS (Model + User)

**Goal:** Convert each blind spot (model + user) into a **learnable unit** — a self-contained knowledge package with verification protocol.

**For each blind spot in `BLIND_SPOT_REGISTER` (priority order), produce a learning unit using this schema** (full worked examples for each category are in `reference.md`):

```markdown
# LEARNING_UNIT-<NNN> (<Model|User>: <CATEGORY>)
## Learning Objective
<what to learn or correct>

## Current Belief (Falsified)
<the assumption that was wrong> — <CATEGORY>, delta <signed delta>

## Corrected Understanding
<the truth the evidence shows — stated directly, not hedged; when the evidence only bounds the truth, state the bound>

## Verification Protocol
1. <minimal decisive checks — 1–3 evidence-generating steps; not a ritual re-verification>
...

## Success Criteria
- <observable outcome>
...

## Knowledge Artifact Template
- **Type**: <ADR | Pattern Doc | Convention + Lint Rule | ...>
- **Location**: `.claude/knowledge/learning-units/<slug>.md`
- **Memory Pointer**: `.claude/projects/<proj>/memory/<slug>.md`
- **Integration**: <which skills to tag>

## Status
PENDING → IN_PROGRESS → VERIFIED → PERSISTED
```

The only per-category variation is the **Current Belief** field: model units cite the model's assumption, `USER_MISALIGNMENT`/`USER_GOAL_TASK_MISMATCH` cite the user's stated goal or mental model, and `USER_TACIT_GAP` cites what the user tacitly assumed. Everything else follows the schema above.

**Output:** Individual `.md` files in `.claude/knowledge/learning-units/<id>.md`

**Rule:** Every `CRITICAL` and `HIGH` blind spot (model + user) MUST produce a learning unit. `MEDIUM` if time permits. `LOW` → `POSSIBLE_BLIND_SPOT` log only.

---

### Phase 5 — KNOWLEDGE BASE UPDATE (Model + User)

**Goal:** Persist verified learnings to the project memory system and local knowledge base — for both model calibration and user context alignment.

**Actions:**
1. **Write learning unit files** to `.claude/knowledge/learning-units/` (both model and user types)
2. **Update memory system** — For each learning unit that represents a durable decision/pattern:
   - Create memory file in `.claude/projects/<proj>/memory/<slug>.md` (frontmatter + body)
   - Update `MEMORY.md` index with wikilink
3. **Update workspace model** — Patch `WORKSPACE_MODEL.md` with verified conventions (status → `FACT`/`WORKSPACE_CONVENTION`)
4. **Update user context model** — Patch `USER_CONTEXT_MODEL.md` with validated user intent/needs/tacit knowledge
5. **Append to calibration log** — Already done in Phase 2, but add summary entry

**Memory File Template (Model):**
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
  source: model_calibration
---

Workspace's architecture is a **modular monolith**, not clean architecture layers.

**Evidence:** Import graph shows core imports runtime/ and system/ directly. No layer separation enforced.

**Why this matters:** Architectural decisions assuming clean architecture will be wrong. Dependency direction is mixed.

**How to apply:** When making architecture decisions, assume modular monolith. Domain logic lives in core. Operational concerns in runtime/. Infrastructure in system/. Cross-layer imports are normal here.

**Falsifier:** If a formal architecture doc (ADR) appears enforcing clean layers, this memory is obsolete.
```

**Memory File Template (User):**
```markdown
---
name: user-architecture-model
description: "User mental model: clean architecture; actual: modular monolith. Gap causes wrong architectural decisions."
metadata:
  node_type: memory
  type: project
  originSessionId: <current-session-id>
  modified: <ISO-timestamp>
  layer: L3
  verified: true
  calibration_delta: -0.80
  source: user_context
  user_misalignment: true
---

User's mental model assumes **clean architecture** (domain/application/infrastructure layers).
Actual workspace is a **modular monolith** with cross-layer imports.

**Evidence:** Import graph shows core imports runtime/ and system/ directly. User explicitly stated "we follow clean architecture" in conversation.

**Why this matters:** User will make architecture decisions assuming clean layers. Actual code violates this. Decisions will be wrong.

**How to apply:** 
- Before architecture tasks, remind user: "Workspace is modular monolith, not clean architecture"
- In `using-agent-skills` pre-check, flag architecture decisions for review
- In `planning-and-task-breakdown`, weight architecture tasks with this misalignment risk

**Falsifier:** If user updates mental model AND workspace gets formal ADR enforcing clean layers.
```

**Write policy:** everything written here goes only to `KNOWLEDGE_ROOT` / `MEMORY_ROOT` (and `--output-dir`) — the audited workspace itself stays read-only. The canonical two-zone rule and fix mode live in **Fix Mode & Write Policy** below. **Provenance on persist:** every persisted record carries its `provenance` and `verified_this_session` flags — persistence never upgrades a belief to FACT.

**Output:** Updated memory index + new memory files + updated workspace model + updated user context model.

---

### Phase 6 — CALIBRATION REPORT (Model + User)

**Goal:** Synthesize session results into actionable summary for current and future sessions — covering both model calibration and user context alignment.

**Report Structure** — display body in this order (full worked example in `reference.md`):

1. **Bottom Line** — 2–3 first-person sentences: how reliable the picture of this workspace is, and the single biggest gap.
2. **Corrected Beliefs** — each belief that turned out wrong, with the evidence and the corrected truth (`corrected_belief`).
3. **Claims Table** — one row per tested/load-bearing claim; the remainder summarized in a single line: `Claim | Tier | Provenance | Confidence | Evidence or check performed`. Confidence is band+score (e.g. `High (0.85)`) for calibration-logged claims, band only otherwise (§2).
4. **Top Blind Spots** — model + user tables by risk (severity × layer_weight, L4=4 … L1=1), with learning-unit status.
5. **Coverage Gaps & Scope Limits** — top of the Blind Area Ranking (never-touched areas), every explicit scope limit, and the scope of every negative search relied on.
6. **Still Unverified** — unconditional (write "none" if empty): every untested testable assumption, every `BLOCKED` check with its `unblock_condition`, and what each would take to settle.
7. **Open Questions** — two-condition gate: only questions that **cannot be settled from the workspace alone** AND whose answer **would change the conclusions**. `BLOCKED`-derived questions are listed regardless of the gate.
8. **Epistemic Buckets** — 4-bucket table: **Established** (directly supported by inspected evidence) / **Uncertain** (plausible, incomplete evidence) / **Not-Yet-Examined** (relevant areas untouched) / **Recommended Probes**.
9. **Stop Reason** — which stop condition fired, and what stopping here costs.

**Recommended Probes rules:** each probe is a concrete executable check (a command to run or a file to read), ordered by expected value; no "consider investigating X" filler (Anti-Pattern #14).

**Appendix** (after the display body): session meta, assumption statistics (model + user context), calibration curve, user context alignment, learning units, cross-model validation, calibration trend, pre-load recommendations.

**Prose standard:** short and scannable; no invented evidence; never imply exhaustive coverage. If the audit found no actionable issue, state what was inspected and what remains outside scope.

**Quick-mode minimum:** Bottom Line + Top Blind Spots + Stop Reason + Open Questions.

**Output:** `CALIBRATION_REPORT.md` (displayed to user) + `CALIBRATION_SUMMARY.json` (machine-readable for `using-agent-skills` pre-check)

---

## Fix Mode & Write Policy (Two Zones)

**Zone A — writable:** `KNOWLEDGE_ROOT` (`${CLAUDE_PROJECT_DIR}/.claude/knowledge/`, or `--output-dir`) and `MEMORY_ROOT` (`${CLAUDE_PROJECT_DIR}/.claude/projects/<slug>/memory/`), plus `SELF_AUDIT_KNOWLEDGE_ROOT` / `SELF_AUDIT_MEMORY_ROOT` overrides. These roots are declared **out of audit scope** — the notebook, not the specimen.

**Zone B — read-only:** everything else. The audited workspace (including `--target plan|diff|last-answer` source material) is inspected, never edited. No edit, delete, install, commit, or state-mutating command anywhere outside Zone A — during the audit or after it (§4 probe safety).

**Fix mode** — proposing and applying workspace changes — runs **only on explicit user request**, after the report:
- Propose concrete changes (fix docs, add a missing test, pin a version); each proposal names the finding it fixes
- Apply only on explicit approval, change by change
- Re-run the relevant checks after applying — an unverified fix is a new assumption
- Self-authorized remediation is an audit failure (Anti-Pattern #12)

**allowed-tools honesty:** the frontmatter `allowed-tools` list is what the harness permits; this policy is narrower and governs.

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
2. **Skipping verification** — "It's obvious" is not a verification result, and a check that cannot return FALSIFIED is not a verification (§4)
3. **Silent confidence inflation** — Confidence must be explicit and can only increase via verification
4. **Generalizing workspace conventions** — Tag with `scope: "this-project"` always
5. **Conflating model knowledge with workspace knowledge** — Distinguish "Python uses indentation" (universal) from "This project uses 4-space indent" (workspace)
6. **Fake precision** — Decorative numbers on unmeasured claims; numeric confidence only for calibration-log entries, HIGH/MEDIUM/LOW band otherwise (§2 measurement split)
7. **Premature generalization** — One counterexample ≠ pattern broken, and one confirming sample ≠ pattern established; require a systematic, scoped check
8. **Silent revision** — Changing conclusions without marking revision in log
9. **Ritual calibration** — Running phases without genuine probes; if workspace is stable and calibration log shows low drift, quick mode is correct
10. **Ignoring cross-model disagreement** — If fresh-context reviewer disagrees, log it as `CONTRADICTION` in calibration log
11. **Fabricated or unobserved evidence** — never invent paths, versions, commands, flags, output, or file contents in **any** record field (`evidence`, `commands_ran`, `verification_method`, …): an empty field is honest, a filled invention is fabrication
12. **Self-authorized remediation** — editing or "fixing" the workspace mid-audit without an explicit request (Fix Mode & Write Policy)
13. **Intuition-directed sweep** — probing only where problems are already expected; the sweep order comes from the coverage ledger and risk ranking, not from hunches (§4 disconfirmation preference)
14. **Filler findings** — padding registers with trivia to look thorough; a small honest register beats a large decorated one
15. **Filename-implies-content** — treating a filename or directory name as evidence of what is inside (§4 observation is a closed set)
16. **Assumed command/flag behavior** — invoking an unconfirmed command, flag, or API and reading its failure as project evidence (§4 version suspicion)
17. **Unexplained inference** — an `INFERRED` claim without a `reasoning_chain` (§1 provenance)
18. **Stale conclusion restatement** — repeating an earlier conclusion in a long session without rechecking; re-observe or mark `finding_kind: STALE_BASIS` (§5 loaded ≠ observed)
19. **Speculation-as-defect** — phrasing `SPECULATION` as a confirmed problem; label it as speculation, never launder it into a finding
20. **Secrets & scope violations** — opening env files, key stores, or credential-bearing config (existence only, §4), or writing outside `KNOWLEDGE_ROOT`/`MEMORY_ROOT` (Fix Mode & Write Policy)

---

## Stop Conditions

Do not run indefinitely. Stop when ANY of A–F is true, or when **G and H hold together**:

- **STOP A**: Workspace model stable; calibration drift < 0.05 over last 3 sessions; no new critical blind spots
- **STOP B**: All L3/L4 blind spots have learning units with `VERIFIED` status
- **STOP C**: Next useful step is execution (user wants to build, not audit)
- **STOP D**: Additional phases producing repetition (no new blind spots in 2 consecutive phases)
- **STOP E**: User has enough information to act
- **STOP F**: Workspace empty or too small to calibrate against — say so plainly and stop early
- **STOP G**: Every load-bearing claim is verified or honestly labeled
- **STOP H**: Further checks would cost more than the decision is worth

**G+H is the stopping rule:** both must hold — labeled-but-unchecked load-bearing claims alone don't justify stopping, and cheap decisive checks remaining don't either. Under `--stakes high`, G alone is acceptable only when no cheap decisive check remains (stakes-cap-wins, §7).

**Closing is three parts, always** (including a zero-findings audit): (1) what was inspected, (2) what remains unknown — list `POSSIBLE_BLIND_SPOT`s, `UNVERIFIED_CRITICAL`s, untested assumptions, `BLOCKED` checks explicitly, (3) what is outside scope. State the stopping point explicitly instead of implying completeness.

---

## Machine-Readable Output (for tooling)

When structured consumption needed (e.g., `using-agent-skills` pre-check):

```json
{
  "skill": "self-audit",
  "mode": "quick|standard|deep",
  "target": "workspace|plan|diff|last-answer",
  "decision_dependency": "whether to proceed with the auth refactor",
  "stakes": "low|medium|high",
  "workspace": "${CLAUDE_PROJECT_DIR}",
  "session_id": "uuid",
  "timestamp": "ISO8601",
  "workspace_model": { "...": "includes coverage_ledger (canonical home) and scope_limits" },
  "assumptions": [
    {"id": "...", "type": "...", "claim_kind": "...", "statement": "...", "confidence": 0.85, "likelihood_band": "HIGH|MEDIUM|LOW", "testable": true, "layer": "L2", "provenance": "OBSERVED_THIS_SESSION|INFERRED|RECALLED|ASSUMED", "verified_this_session": true, "preconditions": [], "edge_cases_unexamined": [], "possible_confusions": [], "result": "CONFIRMED|FALSIFIED|INCONCLUSIVE", "check_status": "RAN|BLOCKED|SKIPPED", "verification_method": "...", "search_scope": { }, "confidence_delta": -0.12, "corrected_belief": "...", "evidence": [...]}
  ],
  "blind_spots": [
    {"id": "...", "category": "...", "layer": "L3", "severity": "Critical", "confidence_delta": -0.72, "likelihood_band": "HIGH|MEDIUM|LOW", "premises": [], "unexamined_paths": [], "smallest_useful_check": "...", "learning_unit_id": "...", "status": "PENDING|IN_PROGRESS|VERIFIED|PERSISTED"}
  ],
  "claims_pending": ["untested testable assumption ids and BLOCKED check ids"],
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
  "recommended_probes": [
    {"check": "rg 'float.*price' billing/", "settles": "ASSUME-019", "value_rank": 1}
  ],
  "recommended_preload": [
    "workspace-model",
    "workspace-architecture-pattern",
    "domain-conventions"
  ],
  "open_questions": [...],
  "stop_reason": "STOP G+H"
}
```

Machine-readable output MUST preserve epistemic status. Do not encode hypotheses as facts. Numeric fields (`confidence`, `confidence_delta`) appear only for calibration-log entries; everything else carries `likelihood_band` (§2) — the same measurement split applies in JSON.

---

## Quick Reference Card

| Phase | Quick | Standard | Deep | Key Output |
|-------|-------|----------|------|------------|
| 0: Workspace Map | ✓ | ✓ | ✓ | `WORKSPACE_MODEL` (+ coverage ledger) |
| 1: Claim & Assumption Capture | Top 20 | All | All + prospective claims + cross-model seeds | `ASSUMPTION_REGISTER` |
| 2: Calibration Tests | Top 10 + load-bearing | Top 25 + load-bearing | Top 50 + all load-bearing + adversarial re-test | `CALIBRATION_LOG` |
| 3: Blind Spot Map | Top 5 + Failure-Mode Scan | All + ranking | All + trend analysis | `BLIND_SPOT_REGISTER` |
| 4: Learnable Units | Critical only | High+ | All + cross-model design | `LEARNING_UNITS/` |
| 5: Knowledge Base Update | Memory only | Full | Full + global sync prep | Memory files |
| Pre-Mortem | Short (3 items) | Standard (3 items) | Extended (3 items + cross-model) | Pre-mortem block |
| 6: Calibration Report | Minimum set | Full | Full + trend + validation | `CALIBRATION_REPORT` |

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