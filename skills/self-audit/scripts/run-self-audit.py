#!/usr/bin/env python3
"""
Self-Audit CLI Wrapper -- Run epistemic calibration on any workspace.
This script is invoked by the skill via allowed-tools Bash substitution.
"""
import argparse
import json
import os
import re
import sys
from pathlib import Path
from datetime import datetime
from typing import Dict, List, Any, Optional

# Domain-adaptive analysis layer (v1.3): schema validators + candidate
# nomination live in a colocated module; semantics stay in SKILL.md.
sys.path.insert(0, str(Path(__file__).parent))
import domain_analysis

class SelfAuditCLI:
    def __init__(self):
        self.skill_dir = Path(os.getenv("CLAUDE_SKILL_DIR", Path(__file__).parent.parent.parent))
        self.workspace = Path(os.getenv("SELF_AUDIT_WORKSPACE", os.getenv("CLAUDE_PROJECT_DIR", "."))).resolve()
        self.knowledge_root = Path(os.getenv("SELF_AUDIT_KNOWLEDGE_ROOT", self.workspace / ".claude" / "knowledge")).resolve()
        self.memory_root = Path(os.getenv("SELF_AUDIT_MEMORY_ROOT", self.workspace / ".claude" / "projects" / self._project_slug() / "memory")).resolve()
        # Real, unique session id — one per run. Trend analysis groups by this,
        # so it must actually differ across runs (not a hardcoded demo value).
        self.session_id = os.getenv("SELF_AUDIT_SESSION_ID") or f"session-{datetime.now().strftime('%Y%m%d-%H%M%S')}"

        # Optional tunables (documented in docs/configuration.md)
        self.verbose = os.getenv("SELF_AUDIT_VERBOSE", "false").lower() == "true"
        self.max_assumptions = int(os.getenv("SELF_AUDIT_MAX_ASSUMPTIONS", "0") or 0)
        self.quick_top_n = int(os.getenv("SELF_AUDIT_QUICK_TOP_N", "5") or 5)
        self.blind_spot_threshold = float(os.getenv("SELF_AUDIT_BLIND_SPOT_THRESHOLD", "0.3") or 0.3)
        self.cross_model_reviewers = max(1, int(os.getenv("SELF_AUDIT_CROSS_MODEL_REVIEWERS", "2") or 2))
        self.trend_min_sessions = max(1, int(os.getenv("SELF_AUDIT_TREND_MIN_SESSIONS", "2") or 2))
        self.user_context = os.getenv("SELF_AUDIT_USER_CONTEXT", "false").lower() == "true"
        # Scope & stakes (SKILL.md §7) — what is being audited, and the verification budget.
        self.target = os.getenv("SELF_AUDIT_TARGET", "workspace")
        self.stakes = os.getenv("SELF_AUDIT_STAKES", "medium")
        # Domain-adaptive layer (v1.3): on by default; env kill-switch.
        self.domain_layer = os.getenv("SELF_AUDIT_DOMAIN_LAYER", "true").lower() == "true"
        # Stated audit purpose (task resolution input); empty = not stated.
        self.audit_purpose = os.getenv("SELF_AUDIT_AUDIT_PURPOSE", "") or ""

    def _project_slug(self) -> str:
        """Generate a safe slug from workspace path."""
        return self.workspace.name.lower().replace(" ", "-").replace(".", "-")

    def _mode_budget(self) -> int:
        """Depth-mode verification budget (SKILL.md): quick 10 / standard 25 / deep 50.

        SELF_AUDIT_MAX_ASSUMPTIONS overrides when set (> 0).
        """
        return self.max_assumptions or {"quick": 10, "standard": 25, "deep": 50}.get(self.mode, 25)

    def run(self, args: argparse.Namespace) -> int:
        """Main entry point."""
        # Ensure output directories exist
        self.knowledge_root.mkdir(parents=True, exist_ok=True)
        self.memory_root.mkdir(parents=True, exist_ok=True)

        print(f"[SCAN] Self-Audit starting...")
        print(f"   Workspace: {self.workspace}")
        print(f"   Knowledge root: {self.knowledge_root}")
        print(f"   Memory root: {self.memory_root}")
        print(f"   Mode: {args.mode}")
        print(f"   Target: {self.target} | Stakes: {self.stakes}")
        self.mode = args.mode

        if args.mode == "quick":
            return self._run_quick_mode()
        elif args.mode == "standard":
            return self._run_standard_mode()
        elif args.mode == "deep":
            return self._run_deep_mode(args)
        else:
            print(f"Unknown mode: {args.mode}")
            return 1

    def _run_quick_mode(self) -> int:
        """Run Phase 0 -> 1 (mode budget) -> 2 (critical) -> 3 -> 6"""
        print("\n[PHASE] QUICK MODE: Phase 0 -> 1 -> 2 -> 3 -> 6")

        # Phase 0: Workspace Map
        workspace_model = self._phase_0_workspace_map()
        self._write_json(self.knowledge_root / "workspace-model.json", workspace_model)
        self._write_markdown(self.knowledge_root / "workspace-model.md", self._format_workspace_model(workspace_model))

        # Phase 1: Assumption Extraction (mode budget, or SELF_AUDIT_MAX_ASSUMPTIONS)
        assumptions = self._phase_1_assumption_extraction(
            workspace_model, max_assumptions=self._mode_budget())
        self._write_json(self.knowledge_root / "assumptions.json", assumptions)

        # Phase 2: Calibration Tests (critical only - L3/L4)
        calibration_log = self._phase_2_calibration_tests(assumptions, critical_only=True)
        self._append_jsonl(self.knowledge_root / "calibration.log.jsonl", calibration_log)

        # Phase 3: Blind Spot Map (top N, or SELF_AUDIT_QUICK_TOP_N)
        blind_spots = self._phase_3_blind_spot_map(calibration_log, top_n=self.quick_top_n)
        self._write_markdown(self.knowledge_root / "blind-spots.md", self._format_blind_spots(blind_spots))

        # Phase 3.5 (domain layer, quick depth): findings + blind-spot
        # candidates only — no domain model, no patterns (depth rules).
        domain_depth = None
        if self.domain_layer:
            domain_depth = domain_analysis.analysis_depth(
                "quick", self.stakes, self._task_complexity(workspace_model))
            self._write_domain_layer_artifacts(
                mode="quick", workspace_model=workspace_model,
                assumptions=assumptions, calibration_log=calibration_log,
                blind_spots=blind_spots, learning_units=[], depth=domain_depth)

        # Phase 6: Calibration Report
        report = self._phase_6_calibration_report(
            mode="quick",
            assumptions=assumptions,
            calibration_log=calibration_log,
            blind_spots=blind_spots,
            learning_units=[]
        )
        self._write_markdown(self.knowledge_root / "calibration-report.md", report)
        self._write_json(self.knowledge_root / "calibration-summary.json", self._format_summary(assumptions, calibration_log, blind_spots))

        print("\n[OK] Quick mode complete!")
        print(f"   Artifacts in: {self.knowledge_root}")
        return 0

    def _run_standard_mode(self) -> int:
        """Run full Phase 0-6 workflow."""
        print("\n[PHASE] STANDARD MODE: Phase 0 -> 1 -> 2 -> 3 -> 4 -> 5 -> 6")

        # Phase 0
        workspace_model = self._phase_0_workspace_map()
        self._write_json(self.knowledge_root / "workspace-model.json", workspace_model)
        self._write_markdown(self.knowledge_root / "workspace-model.md", self._format_workspace_model(workspace_model))

        # Phase 1
        assumptions = self._phase_1_assumption_extraction(
            workspace_model, max_assumptions=self._mode_budget())
        self._write_json(self.knowledge_root / "assumptions.json", assumptions)

        # Phase 2
        calibration_log = self._phase_2_calibration_tests(assumptions, critical_only=False)
        self._append_jsonl(self.knowledge_root / "calibration.log.jsonl", calibration_log)
        # Phase 3
        blind_spots = self._phase_3_blind_spot_map(calibration_log, top_n=15)
        self._write_markdown(self.knowledge_root / "blind-spots.md", self._format_blind_spots(blind_spots))

        # Phase 4
        learning_units = self._phase_4_learnable_units(blind_spots)
        for lu in learning_units:
            # Preserve any already-PERSISTED status on the artifact copy before regenerating it
            self._write_lu_artifact(lu)

        # Phase 3.5 (domain layer, standard depth): task resolution +
        # domain model + findings + patterns + blind-spot candidates.
        domain_depth = None
        if self.domain_layer:
            domain_depth = domain_analysis.analysis_depth(
                "standard", self.stakes, self._task_complexity(workspace_model))
            self._write_domain_layer_artifacts(
                mode="standard", workspace_model=workspace_model,
                assumptions=assumptions, calibration_log=calibration_log,
                blind_spots=blind_spots, learning_units=learning_units,
                depth=domain_depth)

        # Phase 5
        self._phase_5_knowledge_base_update(learning_units, workspace_model)

        # Phase 6
        report = self._phase_6_calibration_report(
            mode="standard",
            assumptions=assumptions,
            calibration_log=calibration_log,
            blind_spots=blind_spots,
            learning_units=learning_units
        )
        self._write_markdown(self.knowledge_root / "calibration-report.md", report)
        self._write_json(self.knowledge_root / "calibration-summary.json", self._format_summary(assumptions, calibration_log, blind_spots, learning_units))

        print("\n[OK] Standard mode complete!")
        return 0

    def _run_deep_mode(self, args: argparse.Namespace) -> int:
        """Run standard + cross-model validation + trend analysis."""
        print("\n[PHASE] DEEP MODE: Standard + Cross-Model Validation + Trend Analysis")

        # Run standard mode first
        ret = self._run_standard_mode()
        if ret != 0:
            return ret

        # Cross-model validation
        cross_model_stats = None
        if not args.no_cross_model and os.getenv("SELF_AUDIT_CROSS_MODEL", "true").lower() == "true":
            cross_model_stats = self._phase_cross_model_validation()
        else:
            # Explicitly disabled: a prior run's log must not survive to be
            # read as reviews that never happened this run.
            self._clear_stale_cross_model_log()

        # Trend analysis
        trend_stats = None
        if not args.no_trend and os.getenv("SELF_AUDIT_TREND_ANALYSIS", "true").lower() == "true":
            trend_stats = self._phase_trend_analysis()

        # Update report with deep mode findings
        self._update_report_for_deep_mode(cross_model_stats, trend_stats)

        print("\n[OK] Deep mode complete!")
        return 0

    # ===== PHASE IMPLEMENTATIONS =====

    def _phase_0_workspace_map(self) -> Dict[str, Any]:
        """Phase 0: Build workspace model."""
        print("  Phase 0: Mapping workspace...")

        model = {
            "domain": self._detect_domain(),
            "target": self.target,
            "stakes": self.stakes,
            "stack": self._detect_stack(),
            "structure": self._inventory_structure(),
            "conventions": self._sample_conventions(),
            "memory_index": self._load_memory_index(),
            "calibration_history": self._load_calibration_history(),
            "open_questions": []
        }

        print(f"    Found {len(model['structure']['source_dirs'])} source dirs, {len(model['conventions'])} candidate conventions")
        return model

    def _phase_05_user_context_discovery(self) -> List[Dict]:
        """Phase 0.5 (user-context mode): Discover user-context signals from the workspace.

        Unlike model assumptions (which describe what the *model* assumes about the code),
        user-context assumptions describe what the *user* needs, intends, or tacitly knows —
        inferred from real workspace signals: stated docs, TODO debt, test coverage shape,
        config drift, and goal-vs-reality mismatch. Read-only, no fabrication.
        """
        if not self.user_context:
            return []

        print("  Phase 0.5: Discovering user context (intent, needs, tacit knowledge, goal fit)...")
        signals: List[Dict] = []

        # 1. Stated intent in docs: "we follow X", "this project uses Y", "the goal is Z"
        doc_claims = []
        stated_patterns = [
            (r"(?:we\s+follow|uses?|is\s+based\s+on)\s+([A-Za-z][A-Za-z0-9\- ]{3,40})", "USER_INTENT"),
            (r"(?:the\s+)?goal\s+is\s+([A-Za-z][^.]{3,80})", "USER_GOAL"),
            (r"(?:must|should|always|never)\s+([A-Za-z][^.]{3,80})", "USER_NEED"),
        ]
        for md in list(self.workspace.rglob("*.md"))[:40]:
            try:
                text = md.read_text(encoding="utf-8", errors="ignore")
            except Exception:
                continue
            for line in text.splitlines():
                for pat, kind in stated_patterns:
                    m = re.search(pat, line, re.IGNORECASE)
                    if m:
                        claim = m.group(1).strip()
                        if 4 <= len(claim) <= 90:
                            doc_claims.append({"kind": kind, "claim": claim, "source": str(md.relative_to(self.workspace))})
        # De-duplicate by claim text, keep first source
        seen = set()
        for c in doc_claims:
            key = c["claim"].lower()
            if key not in seen:
                seen.add(key)
                signals.append(c)

        # 2. Tacit knowledge signals: TODO/FIXME debt the user lives with but never states
        todo_count = 0
        todo_files = set()
        for ext in ("*.py", "*.ts", "*.js", "*.go", "*.rs", "*.java"):
            for f in list(self.workspace.rglob(ext))[:200]:
                try:
                    t = f.read_text(encoding="utf-8", errors="ignore")
                except Exception:
                    continue
                n = len(re.findall(r"\b(TODO|FIXME|HACK|XXX)\b", t))
                if n:
                    todo_count += n
                    todo_files.add(f.name)
        if todo_count > 0:
            signals.append({
                "kind": "USER_TACIT",
                "claim": f"Workspace carries {todo_count} TODO/FIXME markers across {len(todo_files)} files (debt the user tacitly accepts)",
                "source": "source-scan",
            })

        # 3. Goal-task mismatch signals: aspirational docs vs. thin reality
        has_docs = (self.workspace / "docs").exists() or any(self.workspace.glob("*.md"))
        test_dirs = [d for d in ("tests", "test", "__tests__", "spec") if (self.workspace / d).exists()]
        if has_docs and not test_dirs:
            signals.append({
                "kind": "USER_GOAL_MISMATCH",
                "claim": "Workspace documents intent but has no test directory (stated goals not backed by verification)",
                "source": "structure-scan",
            })

        print(f"    Found {len(signals)} user-context signals")
        return signals

    # ===== DOMAIN-ADAPTIVE LAYER (v1.3) =====
    # Semantics (domain modeling, distinction criteria, causal reasoning)
    # live in SKILL.md's agent protocol. These methods build the bounded,
    # deterministic parts: task resolution, seed concepts, pattern
    # candidates, and blind-spot candidates — every heuristic output is a
    # CANDIDATE nomination, never a finding.

    def _task_complexity(self, workspace_model: Dict) -> str:
        """Bounded complexity estimate (SIMPLE|MULTISTEP|UNCERTAIN).

        Deterministic default; the agent may override in its own report.
        UNCERTAIN when >20% of last session's checks were INCONCLUSIVE.
        """
        conventions = len(workspace_model.get("conventions", []))
        test_dirs = workspace_model.get("structure", {}).get("test_dirs", [])
        inconclusive_ratio = 0.0
        history = workspace_model.get("calibration_history", [])
        if history:
            last = history[-1]
            total = last.get("total_assumptions", 0)
            if total > 0:
                # measured = CONFIRMED + FALSIFIED; everything else
                # (INCONCLUSIVE/SKIPPED/KNOWN_FALSE) is unresolved signal
                confirmed = last.get("confirmed_count", 0)
                falsified = last.get("falsified_count", 0)
                inconclusive_ratio = max(0.0, (total - confirmed - falsified)) / total
        if inconclusive_ratio > 0.2:
            return "UNCERTAIN"
        if conventions < 3 and not test_dirs:
            return "SIMPLE"
        return "MULTISTEP"

    def _phase_0_6_task_resolution(self, workspace_model: Dict) -> Dict:
        """Phase 0.6: persist the §7 scope statement as task resolution.

        Fields mirror domain_analysis.TASK_RESOLUTION_FIELDS. The stated
        outcome comes from --audit-purpose / SELF_AUDIT_AUDIT_PURPOSE when
        given; otherwise it is honestly marked as not stated (an INFERENCE,
        never presented as user intent).
        """
        env_overrides = [k for k in (
            "SELF_AUDIT_WORKSPACE", "SELF_AUDIT_KNOWLEDGE_ROOT",
            "SELF_AUDIT_MEMORY_ROOT", "SELF_AUDIT_TARGET", "SELF_AUDIT_STAKES",
        ) if os.getenv(k)]
        access_limits = [
            "CLI scans the workspace tree only; files outside the workspace root are not read",
            "untracked/ignored directories are included in scans but their semantics are not verified",
        ]
        if self.target in ("plan", "diff", "last-answer"):
            access_limits.append(
                f"target '{self.target}' has no CLI-side content ingestion — "
                f"the flag is recorded but the content is audited by the agent, not this script")
        task_resolution: Dict[str, Any] = {
            "stated_outcome": self.audit_purpose or
                "not stated — inferred from workspace scan",
            "inferred_purpose": {
                "purpose": "calibrate the model's beliefs about this workspace "
                           "before acting on them",
                "labeled_as": "INFERENCE",
                "basis": "self-audit skill default when no purpose is stated",
            } if not self.audit_purpose else None,
            "object_of_analysis": self.target,
            "resource_scope": {
                "workspace": str(self.workspace),
                "env_overrides": env_overrides,
            },
            "access_limits": access_limits,
            "complexity": self._task_complexity(workspace_model),
            "cost_of_error": f"wrong beliefs at {self.stakes} stakes would misdirect "
                             f"decisions relying on this workspace picture",
            "verification_criteria": "every load-bearing claim checked or honestly "
                                     "labeled (SKILL.md §4, §7)",
            "open_clarifications": [],
        }
        if task_resolution["inferred_purpose"] is None:
            task_resolution.pop("inferred_purpose")
        return task_resolution

    def _phase_0_7_domain_model(self, workspace_model: Dict) -> Dict:
        """Phase 0.7: derive SEED concepts from real scans.

        Every concept comes from an observed artifact (convention, stack
        entry, structure entry). 'distinguishes' starts empty — Python
        cannot invent criteria; the agent fills them. A concept is
        ESTABLISHED only when its convention already passed Phase 2 as
        WORKSPACE_CONVENTION in the calibration history; otherwise
        PROPOSED (provisional, requires verification).
        """
        verified_patterns = set()
        log_path = self.knowledge_root / "calibration.log.jsonl"
        if log_path.exists():
            for line in log_path.read_text(encoding="utf-8").strip().split("\n"):
                if not line.strip():
                    continue
                try:
                    r = json.loads(line)
                except Exception:
                    continue
                if r.get("new_status") == "WORKSPACE_CONVENTION" and r.get("result") == "CONFIRMED":
                    verified_patterns.add(r.get("prediction", ""))

        concepts = []
        for conv in workspace_model.get("conventions", []):
            pattern_text = conv.get("pattern", "")
            if not pattern_text:
                continue
            name = re.sub(r"[^a-z0-9]+", "-", pattern_text.lower()).strip("-")[:50]
            established = any(pattern_text in vp for vp in verified_patterns)
            concepts.append({
                "name": name,
                "definition": f"Observed pattern: {pattern_text} (frequency {conv.get('frequency', 0)})",
                "distinguishes": [],
                "status": "ESTABLISHED" if established else "PROPOSED",
                "source": "workspace-scan",
            })
        for lang in workspace_model.get("stack", {}).get("languages", []):
            concepts.append({
                "name": f"language-{re.sub(r'[^a-z0-9]+', '-', lang.lower()).strip('-')[:40]}",
                "definition": f"Detected language: {lang}",
                "distinguishes": [],
                "status": "PROPOSED",
                "source": "stack-detection",
            })

        coverage_gaps = []
        structure = workspace_model.get("structure", {})
        if not structure.get("test_dirs"):
            coverage_gaps.append("no test directories detected — testing conventions unclassified")
        if not workspace_model.get("conventions"):
            coverage_gaps.append("no conventions detected — convention concepts unclassified")

        model = {
            "subject": f"{self.workspace.name} ({self.target})",
            "concepts": concepts,
            "coverage_notes": coverage_gaps or
                "all scanned areas produced at least one candidate concept",
        }
        return model

    def _evidence_contents(self, refs: List[str]) -> Dict[str, str]:
        """Read workspace-relative evidence refs (bounded, read-only) so
        pattern independence can be content-deduped: identical copies are
        ONE source. Evidence refs are often "path:line" (from doc scans) —
        the file part is resolved for reading while the original ref stays
        the map key. Unreadable refs are omitted (the count stays
        provisional; the caller records that in the note)."""
        contents: Dict[str, str] = {}
        for ref in refs:
            if not ref or ref.startswith("("):
                continue
            # Strip only a numeric :<line> suffix ("docs/a.md:12" -> "docs/a.md")
            ref_file = ref
            base, sep, suffix = ref.rpartition(":")
            if sep and suffix.isdigit() and base:
                ref_file = base
            ref_path = (self.workspace / ref_file).resolve()
            try:
                ref_path.relative_to(self.workspace)
            except ValueError:
                continue  # ref escapes the workspace — not observed
            try:
                if ref_path.is_file() and ref_path.stat().st_size <= 1_000_000:
                    contents[ref] = ref_path.read_text(encoding="utf-8", errors="ignore")
            except OSError:
                continue
        return contents

    def _phase_2_5_pattern_candidates(self, calibration_log: List[Dict]) -> List[Dict]:
        """Phase 2.5: nominate pattern candidates from measured records.

        Only CONFIRMED/FALSIFIED records (real outcomes) feed nomination;
        every candidate is status=CANDIDATE with lexical_signal recorded —
        a lexical signal nominates, it never establishes a pattern.
        Independence is content-deduped: identical file copies count as
        one source, never independent evidence.
        """
        findings = []
        for r in calibration_log:
            if r.get("result") not in ("CONFIRMED", "FALSIFIED"):
                continue
            findings.append({
                "id": r.get("assumption_id", ""),
                "statement": r.get("prediction", ""),
                "source_refs": [str(e) for e in (r.get("evidence") or [])][:5],
            })
        candidates = domain_analysis.nominate_pattern_candidates(findings)
        # Re-map member ids from ASSUME- ids to their statement keys; the
        # caller links candidates to findings by assumption_id.
        for c in candidates:
            c["member_assumption_ids"] = c.pop("member_finding_ids")
            ref_contents = self._evidence_contents(c.get("source_refs", []))
            deduped = domain_analysis.distinct_source_count(
                c.get("source_refs", []), ref_contents)
            c["independence"] = {
                "distinct_sources": deduped,
                "note": ("content dedupe applied over "
                         f"{len(ref_contents)} readable ref(s); identical copies count "
                         "once"
                         + ("" if ref_contents else
                            " (provisional: no ref contents readable)")),
            }
        return candidates

    def _phase_3_5_blind_spot_search(self, workspace_model: Dict,
                                     assumptions: List[Dict],
                                     calibration_log: List[Dict]) -> List[Dict]:
        """Phase 3.5: systematic gap sweep — what Phase 0 mapped vs what
        Phase 1/2 touched. Uses only categories already in the codebase's
        vocabulary; each candidate says why it matters and names the
        smallest useful check (from the linked assumption's falsifier)."""
        candidates = []
        idx = 1
        assumption_by_id = {a.get("id"): a for a in assumptions}

        # 1. INCONCLUSIVE load-bearing claims (L3/L4)
        for r in calibration_log:
            if r.get("result") == "INCONCLUSIVE" and r.get("layer") in ("L3", "L4"):
                a = assumption_by_id.get(r.get("assumption_id"), {})
                candidates.append({
                    "id": f"BSX-{idx:03d}",
                    "description": f"Load-bearing claim unresolved: {r.get('prediction', '')[:150]}",
                    "why_it_matters": f"{r.get('layer')} claim affects system-level decisions; "
                                      f"its falsifier was never decisively checked",
                    "smallest_useful_check": a.get("falsifier") or
                        r.get("inconclusive_reason", "re-run the decisive check"),
                    "category": "UNVERIFIED_CRITICAL",
                })
                idx += 1

        # 2. Structure dimensions mapped but never sampled
        structure = workspace_model.get("structure", {})
        has_docs = bool(structure.get("doc_dirs")) or \
            (self.workspace / "README.md").exists()
        test_dirs = structure.get("test_dirs", [])
        if has_docs and not test_dirs:
            candidates.append({
                "id": f"BSX-{idx:03d}",
                "description": "Docs exist but no test directory was found — "
                               "documented behavior may be unbacked by checks",
                "why_it_matters": "doc claims used as evidence without test backing "
                                  "can misdirect L3/L4 decisions",
                "smallest_useful_check": "search the workspace for any test runner "
                                         "config or test files (rglob tests/test/spec dirs)",
                "category": "DOMAIN_GAP",
            })
            idx += 1

        # 3. Convention frequency drift vs prior session
        history = workspace_model.get("calibration_history", [])
        if len(history) >= 2:
            prev, last = history[-2], history[-1]
            if last.get("falsified_count", 0) > prev.get("falsified_count", 0):
                candidates.append({
                    "id": f"BSX-{idx:03d}",
                    "description": "Falsified count rose between the last two sessions — "
                                   "workspace conventions may be drifting",
                    "why_it_matters": "prior learning units may be stale "
                                      "(MEMORY_DRIFT risk for stored conventions)",
                    "smallest_useful_check": "re-run the falsified assumptions' checks "
                                             "and compare against the stored memory",
                    "category": "MEMORY_DRIFT",
                })
                idx += 1

        # 4. Domain-model concepts with zero findings are surfaced via the
        # domain model's coverage_notes (honest gaps), not as candidates.

        # 5. Docs claiming checks that no source file defines (Test E:
        #    missing-check discovery). Bounded deterministic scan — the doc
        #    names a check/validate/verify symbol in backticks; zero code
        #    hits within the stated scope means the claimed check cannot
        #    back conclusions. Absence is scoped, never "does not exist".
        claimed: List[str] = []
        claim_re = re.compile(
            r"(?i)\b(check|validat\w*|verif\w*)\b[^.\n]{0,80}?`([A-Za-z_][A-Za-z0-9_]*)(?:\(\))?`")
        for f, text in self._iter_text_files(suffixes={".md"}):
            for m in claim_re.finditer(text):
                symbol = m.group(2)
                if symbol not in claimed:
                    claimed.append(symbol)
                if len(claimed) >= 5:
                    break
            if len(claimed) >= 5:
                break
        code_symbols = set()
        for f, text in self._iter_text_files():
            if f.suffix == ".md":
                continue
            code_symbols |= set(re.findall(r"\b[A-Za-z_][A-Za-z0-9_]{2,}\b", text))
        for symbol in claimed:
            if symbol in code_symbols:
                continue
            candidates.append({
                "id": f"BSX-{idx:03d}",
                "description": f"Docs claim a check '{symbol}' that no source file in scope defines",
                "why_it_matters": "conclusions relying on that claimed check rest on an "
                                  "unverified assumption — the check cannot back them",
                "smallest_useful_check": f"search the workspace for the definition of "
                                         f"'{symbol}' (rg '\\b{symbol}\\b' -g '!*.md') "
                                         f"and open the first hit",
                "category": "DOMAIN_GAP",
            })
            idx += 1

        return candidates[:10]

    def _phase_1_assumption_extraction(self, workspace_model: Dict, max_assumptions: int) -> List[Dict]:
        """Phase 1: Extract implicit assumptions."""
        print("  Phase 1: Extracting assumptions...")

        assumptions = []
        assumption_id = 1

        # From conventions
        for conv in workspace_model["conventions"][:10]:
            if assumption_id > max_assumptions:
                break
            assumptions.append({
                "id": f"ASSUME-{assumption_id:03d}",
                "type": "CONVENTION",
                "statement": f"All {conv['pattern']} follow the observed pattern",
                "source_evidence": f"WORKSPACE_MODEL.conventions (frequency {conv['frequency']})",
                # Confidence is a 0.0-1.0 quantity (§2) — frequency raises it, capped at 0.95
                "confidence": min(0.95, 0.75 + (conv["frequency"] * 0.02)),
                "testable": True,
                "layer": "L2",
                "scope": "workspace",
                "falsifier": f"Find a file violating {conv['pattern']} pattern"
            })
            assumption_id += 1

        # Architectural assumptions
        arch_patterns = [
            ("Clean architecture layers (domain/app/infra)", "L3"),
            ("Modular monolith with central core", "L3"),
            ("Microservices with async communication", "L3"),
            ("Layered architecture with strict boundaries", "L3"),
        ]
        for pattern, layer in arch_patterns:
            if assumption_id > max_assumptions:
                break
            assumptions.append({
                "id": f"ASSUME-{assumption_id:03d}",
                "type": "ARCHITECTURAL",
                "statement": f"Workspace follows {pattern}",
                "source_evidence": "WORKSPACE_MODEL.structure + import graph analysis",
                "confidence": 0.85,
                "testable": True,
                "layer": layer,
                "scope": "workspace",
                "falsifier": f"Import graph shows violations of {pattern}"
            })
            assumption_id += 1

        # Domain assumptions
        if workspace_model["domain"]:
            assumptions.append({
                "id": f"ASSUME-{assumption_id:03d}",
                "type": "DOMAIN",
                "statement": f"Domain follows {workspace_model['domain']} conventions",
                "source_evidence": "WORKSPACE_MODEL.domain + domain docs",
                "confidence": 0.7,
                "testable": True,
                "layer": "L4",
                "scope": "workspace",
                "falsifier": "Domain docs contradict this convention"
            })
            assumption_id += 1

        # User-context assumptions (Phase 0.5 signals), enabled by --user-context
        if self.user_context:
            uc_signals = self._phase_05_user_context_discovery()
            uc_type_map = {
                "USER_INTENT": ("USER_INTENT", "L3", 0.8, "Stated intent in docs matches workspace reality"),
                "USER_GOAL": ("USER_GOAL", "L3", 0.75, "Stated goal is achievable given workspace constraints"),
                "USER_NEED": ("USER_NEED", "L2", 0.7, "Stated requirement is enforced/consistent in workspace"),
                "USER_TACIT": ("USER_TACIT", "L4", 0.85, "Tacit assumption (debt/idiom) holds across workspace"),
                "USER_GOAL_MISMATCH": ("USER_GOAL", "L3", 0.7, "Goal can be pursued without scaffolding gaps"),
            }
            for sig in uc_signals:
                if assumption_id > max_assumptions + 10:  # headroom for user-context
                    break
                kind, layer, conf, falsifier = uc_type_map.get(sig["kind"], ("USER_INTENT", "L3", 0.7, "Workspace contradicts this"))
                assumptions.append({
                    "id": f"ASSUME-{assumption_id:03d}",
                    "type": "USER_CONTEXT",
                    "user_context_kind": kind,
                    "statement": f"User assumption: {sig['claim']}",
                    "source_evidence": f"USER_CONTEXT_DISCOVERY ({sig['source']})",
                    "confidence": conf,
                    "testable": True,
                    "layer": layer,
                    "scope": "user",
                    "falsifier": falsifier
                })
                assumption_id += 1
            if uc_signals:
                print(f"    + {len(uc_signals)} user-context assumptions (from Phase 0.5)")

        print(f"    Extracted {len(assumptions)} assumptions")
        return assumptions

    def _phase_2_calibration_tests(self, assumptions: List[Dict], critical_only: bool) -> List[Dict]:
        """Phase 2: Test assumptions against evidence."""
        print("  Phase 2: Running calibration tests...")

        # FIX 1: Load known-falsified assumptions from prior sessions
        known_false = self._load_known_falsified()
        if known_false:
            print(f"    [MEMORY] {len(known_false)} assumptions already FALSIFIED (skipping re-test)")

        calibration_log = []
        tested = 0
        skipped = 0
        deferred = 0

        # Risk order (SKILL.md Phase 1 priority rule): risk = layer weight x
        # (1 - confidence), descending. The budget cuts the tail, never the head.
        layer_weight = {"L4": 4, "L3": 3, "L2": 2, "L1": 1}
        ordered = sorted(
            (a for a in assumptions if a.get("testable")),
            key=lambda a: layer_weight.get(a["layer"], 1) * (1.0 - float(a.get("confidence", 0.5))),
            reverse=True,
        )
        # Depth-mode budget (SKILL.md): quick 10 / standard 25 / deep 50,
        # overridable via SELF_AUDIT_MAX_ASSUMPTIONS. No hard-coded caps.
        budget = self._mode_budget()

        for assumption in ordered:
            if critical_only and assumption["layer"] not in ("L3", "L4"):
                continue

            # FIX 1: Skip if already falsified in prior session
            if assumption["id"] in known_false:
                skipped += 1
                # Record as KNOWN FALSE (not re-tested)
                calibration_log.append({
                    "assumption_id": assumption["id"],
                    "timestamp": datetime.now().isoformat(),
                    "prediction": assumption["statement"],
                    "actual": known_false[assumption["id"]]["actual"],
                    "evidence": known_false[assumption["id"]].get("evidence", []),
                    "result": "KNOWN_FALSE",
                    "confidence_delta": known_false[assumption["id"]].get("confidence_delta", -0.7),
                    "new_status": "PERSISTENT_CALIBRATION_ERROR",
                    "layer": assumption["layer"],
                    "check_status": "SKIPPED",
                    "verification_method": "memory_crosscheck",
                    "search_scope": None,
                    "commands_ran": [],
                    "commands_assumed": [],
                    "session_id": self.session_id
                })
                print(f"    [SKIP] {assumption['id']}: KNOWN FALSE (from prior sessions)")
                continue

            # Stakes-cap-wins (SKILL.md §7): under --stakes high every load-bearing
            # (L3/L4) claim is checked regardless of budget. Deferred claims are
            # counted and reported — never silently dropped.
            load_bearing = assumption["layer"] in ("L3", "L4")
            if tested >= budget and not (self.stakes == "high" and load_bearing):
                deferred += 1
                continue

            tested += 1
            result = self._test_assumption(assumption)
            calibration_log.append(result)

            status = {"CONFIRMED": "[OK]", "FALSIFIED": "[FAIL]", "INCONCLUSIVE": "[?]",
                      "SKIPPED": "[SKIP]", "KNOWN_FALSE": "[SKIP]"}.get(result["result"], "[?]")
            print(f"    {status} {assumption['id']}: {result['result']} (delta: {result['confidence_delta']:.2f})")
            if self.verbose:
                print(f"        evidence: {result.get('evidence', [])}  method: {result.get('verification_method')}")
                print(f"        prediction: {result['prediction'][:100]}")
                print(f"        actual: {result['actual'][:100]}")

        print(f"    Tested {tested} assumptions (budget {budget}), skipped {skipped} known-false")
        if deferred:
            print(f"    [BUDGET] {deferred} lower-risk assumptions deferred over budget (rerun with --stakes high or SELF_AUDIT_MAX_ASSUMPTIONS to cover)")
        return calibration_log

    def _load_known_falsified(self) -> Dict[str, Dict]:
        """FIX 1: Load assumptions that were already falsified in prior sessions."""
        known = {}
        log_path = self.knowledge_root / "calibration.log.jsonl"
        if log_path.exists():
            for line in log_path.read_text(encoding="utf-8").strip().split("\n"):
                if line.strip():
                    try:
                        r = json.loads(line)
                        if r.get("result") == "FALSIFIED":
                            aid = r.get("assumption_id")
                            if aid and aid not in known:
                                known[aid] = {
                                    "actual": r.get("actual", ""),
                                    "evidence": r.get("evidence", []),
                                    "confidence_delta": r.get("confidence_delta", -0.7),
                                    "count": 1
                                }
                            elif aid:
                                known[aid]["count"] += 1
                    except Exception:
                        pass
        return known

    def _phase_3_blind_spot_map(self, calibration_log: List[Dict], top_n: int) -> List[Dict]:
        """Phase 3: Identify blind spots from calibration results."""
        print("  Phase 3: Mapping blind spots...")

        blind_spots = []
        bs_id = 1

        for record in calibration_log:
            if record["result"] == "FALSIFIED" and abs(record.get("confidence_delta", 0)) >= self.blind_spot_threshold:
                layer_weight = {"L4": 4, "L3": 3, "L2": 2, "L1": 1}[record["layer"]]
                severity = "Critical" if record["layer"] in ("L3", "L4") and abs(record["confidence_delta"]) > 0.5 else \
                          "High" if record["layer"] in ("L3", "L4") or abs(record["confidence_delta"]) > 0.5 else \
                          "Medium" if record["layer"] == "L2" else "Low"

                # User-context blind spots get USER_* categories; model ones get CALIBRATION_ERROR
                is_user = record.get("user_context") or record.get("new_status", "").startswith("USER_")
                category = record.get("new_status", "CALIBRATION_ERROR") if is_user else "CALIBRATION_ERROR"
                if category in ("USER_INTENT_VALIDATED", "USER_GOAL_VALIDATED"):
                    category = "CALIBRATION_ERROR"  # validated user assumptions aren't blind spots

                blind_spots.append({
                    "id": f"BS-{bs_id:03d}",
                    "category": category,
                    "layer": record["layer"],
                    "severity": severity,
                    "assumption_id": record["assumption_id"],
                    "assumption_statement": record["prediction"],
                    "evidence_summary": record["actual"][:200],
                    "corrected_belief": record.get("corrected_belief", ""),
                    "confidence_delta": record["confidence_delta"],
                    "discoverability": "Easy" if record["layer"] in ("L1", "L2") else "Moderate",
                    "impact": f"Decisions based on false {record['layer']} assumption",
                    "learning_objective": f"Learn actual {record['layer'].lower()} pattern",
                    "verification_protocol": f"Systematic verification of {record['layer'].lower()} conventions",
                    "integration_points": ["doubt-driven-development", "context-engineering"],
                    "learning_unit_id": f"LU-{bs_id:03d}",
                    "status": "NEW"
                })
                bs_id += 1

        # Sort by risk = severity_weight * layer_weight
        severity_weight = {"Critical": 4, "High": 3, "Medium": 2, "Low": 1}
        layer_weight = {"L4": 4, "L3": 3, "L2": 2, "L1": 1}

        blind_spots.sort(key=lambda b: severity_weight[b["severity"]] * layer_weight[b["layer"]], reverse=True)

        # FIX 2: Detect recurring blind spots (same assumption falsified >=3 times across sessions)
        recurring = self._detect_recurring_errors(calibration_log)
        for rec in recurring:
            existing = [b for b in blind_spots if b["assumption_id"] == rec["assumption_id"]]
            if existing:
                # Upgrade severity to PERSISTENT_BLIND_SPOT
                existing[0]["category"] = "PERSISTENT_BLIND_SPOT"
                existing[0]["severity"] = "Critical"
                existing[0]["status"] = "RECURRING"
                existing[0]["impact"] = f"RECURRING: {rec['count']}x falsified across sessions"
                existing[0]["learning_unit_status"] = "PERSISTED"
            else:
                # Add as new recurring blind spot
                idx = len(blind_spots) + 1
                blind_spots.append({
                    "id": f"BS-REC-{idx:03d}",
                    "category": "PERSISTENT_BLIND_SPOT",
                    "layer": rec["layer"],
                    "severity": "Critical",
                    "assumption_id": rec["assumption_id"],
                    "assumption_statement": rec["prediction"],
                    "evidence_summary": rec["actual"][:200],
                    "corrected_belief": rec.get("corrected_belief", ""),
                    "confidence_delta": rec["confidence_delta"],
                    "discoverability": "Moderate",
                    "impact": f"RECURRING: {rec['count']}x falsified across sessions",
                    "learning_objective": f"Permanently learn {rec['layer'].lower()} pattern",
                    "verification_protocol": f"Document {rec['layer'].lower()} convention in ADR and enforce",
                    "integration_points": ["doubt-driven-development", "context-engineering"],
                    "learning_unit_id": f"LU-PERSIST-{idx:03d}",
                    "status": "RECURRING",
                    "learning_unit_status": "PERSISTED"
                })

        print(f"    Identified {len(blind_spots)} blind spots (top {top_n}), {len(recurring)} recurring")
        if self.verbose:
            for b in blind_spots[:top_n]:
                print(f"        {b['id']} [{b['category']}] {b['layer']}/{b['severity']} risk={b['confidence_delta']:.2f}")
        return blind_spots[:top_n]

    def _detect_recurring_errors(self, calibration_log: List[Dict]) -> List[Dict]:
        """FIX 2: Detect assumptions falsified >=3 times across sessions."""
        from collections import Counter
        falsified_counts = Counter()
        falsified_data = {}

        # Count from this session's log
        for r in calibration_log:
            if r.get("result") in ("FALSIFIED", "KNOWN_FALSE"):
                aid = r.get("assumption_id")
                falsified_counts[aid] += 1
                falsified_data[aid] = r

        # Also count the historical log (prior FALSIFIED records)
        log_path = self.knowledge_root / "calibration.log.jsonl"
        if log_path.exists():
            for line in log_path.read_text(encoding="utf-8").strip().split("\n"):
                if line.strip():
                    try:
                        r = json.loads(line)
                        if r.get("result") == "FALSIFIED":
                            aid = r.get("assumption_id")
                            falsified_counts[aid] += 1
                    except Exception:
                        pass

        recurring = []
        for aid, count in falsified_counts.items():
            if count >= 3 and aid in falsified_data:
                data = falsified_data[aid].copy()
                data["count"] = count
                recurring.append(data)

        return recurring

    def _phase_4_learnable_units(self, blind_spots: List[Dict]) -> List[Dict]:
        """Phase 4: Synthesize learnable units."""
        print("  Phase 4: Synthesizing learning units...")

        learning_units = []

        for bs in blind_spots:
            if bs["severity"] in ("Critical", "High"):
                # FIX 3: Carry over PERSISTED status for recurring blind spots
                initial_status = bs.get("learning_unit_status", "VERIFIED")
                lu = {
                    "id": bs["learning_unit_id"],
                    "blind_spot_id": bs["id"],
                    "layer": bs["layer"],
                    "status": initial_status,
                    "content": self._format_learning_unit(bs),
                    # Domain layer (v1.3): pass-through optional links so
                    # _format_memory_file can emit the optional metadata.
                    "related_findings": bs.get("related_findings"),
                    "reverify_on": (bs.get("reverify_triggers")
                                    if isinstance(bs.get("reverify_triggers"), str)
                                    else "; ".join(bs.get("reverify_triggers") or [])
                                    or None),
                }
                learning_units.append(lu)

        print(f"    Created {len(learning_units)} learning units")
        return learning_units

    def _phase_5_knowledge_base_update(self, learning_units: List[Dict], workspace_model: Dict):
        """Phase 5: Persist to memory system."""
        print("  Phase 5: Updating knowledge base...")

        # Update memory index
        memory_index_path = self.memory_root / "MEMORY.md"
        if memory_index_path.exists():
            content = memory_index_path.read_text()
        else:
            content = "# Memory index\n\n"

        new_count = 0
        verified_count = 0
        persisted = 0
        for lu in learning_units:
            # FIX 3: Proper LU lifecycle - PENDING -> VERIFIED -> PERSISTED
            mem_file = self.memory_root / f"{lu['id'].lower()}.md"
            if not mem_file.exists():
                # Fresh learning unit from a FALSIFIED assumption -> write as VERIFIED
                slug = lu["id"].lower().replace("-", "-")
                pointer = f"- [{lu['id']}]({slug}.md) -- {lu['content'].split(chr(10))[2] if len(lu['content'].split(chr(10))) > 2 else 'Learning unit'}\n"
                if pointer not in content:
                    content += pointer
                lu["status"] = "VERIFIED"
                lu["learning_unit_status"] = "VERIFIED"
                mem_content = self._format_memory_file(lu)
                mem_file.write_text(mem_content)
                print(f"    [NEW] {lu['id']} -> VERIFIED (written to memory)")
                new_count += 1
                continue

            # Memory file already exists -> advance the lifecycle based on current status
            mem_content = mem_file.read_text(encoding="utf-8")
            if "## Status: PERSISTED" in mem_content:
                # Already cross-session verified -> stay PERSISTED, ensure artifact matches
                self._sync_lu_status(lu['id'], "VERIFIED", "PERSISTED (cross-session verified)")
                self._sync_lu_status(lu['id'], "PENDING", "PERSISTED (cross-session verified)")
                lu["status"] = "PERSISTED"
                lu["learning_unit_status"] = "PERSISTED"
                print(f"    [PERSISTED] {lu['id']} (already cross-session verified)")
                persisted += 1
            elif "## Status: VERIFIED" in mem_content:
                # Was VERIFIED in a prior run, seen again now -> promote to PERSISTED (cross-session)
                new_status = "PERSISTED (cross-session verified)"
                mem_content = mem_content.replace("## Status: VERIFIED", f"## Status: {new_status}")
                mem_content = mem_content.replace(
                    "## Corrected Understanding (Hypothesis)\nTo be determined via verification protocol.",
                    "## Corrected Understanding\n"
                    "This calibration error has been observed consistently "
                    "across sessions; the pattern is treated as established workspace knowledge."
                )
                mem_content = mem_content.replace(
                    "## Corrected Understanding\nTo be determined via verification protocol.",
                    "## Corrected Understanding\n"
                    "This calibration error has been observed consistently "
                    "across sessions; the pattern is treated as established workspace knowledge."
                )
                mem_file.write_text(mem_content)
                self._sync_lu_status(lu['id'], "VERIFIED", new_status)
                lu["status"] = "PERSISTED"
                lu["learning_unit_status"] = "PERSISTED"
                print(f"    [PERSISTED] {lu['id']} (VERIFIED -> PERSISTED, cross-session)")
                persisted += 1
            else:
                # Still PENDING -> promote to VERIFIED (learning unit is now backed by evidence)
                mem_content = mem_content.replace("## Status: PENDING", "## Status: VERIFIED")
                mem_file.write_text(mem_content)
                self._sync_lu_status(lu['id'], "PENDING", "VERIFIED")
                lu["status"] = "VERIFIED"
                lu["learning_unit_status"] = "VERIFIED"
                print(f"    [VERIFIED] {lu['id']} (PENDING -> VERIFIED)")
                verified_count += 1

        memory_index_path.write_text(content)

        # Also advance orphaned LUs left in memory or learning-units from prior runs:
        # PENDING -> VERIFIED (now backed by evidence), and prior-session VERIFIED ->
        # PERSISTED (the correction carried into a later session — cross-session stable).
        # Scoped to LU files only (lu-*.md) so unrelated memory entries are never touched.
        current_ids = {lu["id"].upper() for lu in learning_units}
        orphan_dirs = [self.memory_root, self.knowledge_root / "learning-units"]
        for orphan_dir in orphan_dirs:
            if orphan_dir.exists():
                for lu_file in sorted(orphan_dir.glob("*.md")):
                    if not lu_file.stem.lower().startswith("lu") or lu_file.stem.upper() in current_ids:
                        continue  # non-LU memory entry, or this session's LU (handled above)
                    lu_text = lu_file.read_text(encoding="utf-8")
                    if "## Status: PENDING" in lu_text:
                        lu_text = lu_text.replace("## Status: PENDING", "## Status: VERIFIED")
                        lu_file.write_text(lu_text)
                        verified_count += 1
                    elif "## Status: VERIFIED" in lu_text:
                        lu_text = lu_text.replace("## Status: VERIFIED", "## Status: PERSISTED (cross-session verified)")
                        lu_text = lu_text.replace(
                            "## Corrected Understanding\nTo be determined via verification protocol.",
                            "## Corrected Understanding\n"
                            "Carried across sessions and re-observed as stable workspace knowledge."
                        )
                        lu_file.write_text(lu_text)
                        persisted += 1

        print(f"    Knowledge base: {new_count} new -> VERIFIED, {verified_count} promoted, {persisted} PERSISTED (total: {len(learning_units)})")

    def _sync_lu_status(self, lu_id: str, old_status: str, new_status: str):
        """Keep the learning-units/ artifact copy in sync with the memory copy status."""
        artifact = self.knowledge_root / "learning-units" / f"{lu_id}.md"
        if artifact.exists():
            text = artifact.read_text(encoding="utf-8")
            marker_old = f"## Status: {old_status}"
            if marker_old in text:
                text = text.replace(marker_old, f"## Status: {new_status}")
                artifact.write_text(text)

    def _write_lu_artifact(self, lu: Dict):
        """Write the learning-units/ artifact, preserving an already-PERSISTED status line."""
        artifact = self.knowledge_root / "learning-units" / f"{lu['id']}.md"
        preserved_status = None
        if artifact.exists():
            prev = artifact.read_text(encoding="utf-8")
            for line in prev.splitlines():
                if line.startswith("## Status:"):
                    preserved_status = line
                    break
        content = lu['content']
        if preserved_status and "PERSISTED" in preserved_status:
            # Keep the advanced status instead of resetting to VERIFIED
            content = content.replace("## Status: VERIFIED", preserved_status)
        lu['content'] = content
        self._write_markdown(artifact, content)

    def _phase_6_calibration_report(self, mode: str, assumptions: List, calibration_log: List,
                                     blind_spots: List, learning_units: List) -> str:
        """Phase 6: Generate calibration report."""
        print("  Phase 6: Generating calibration report...")

        confirmed = sum(1 for r in calibration_log if r["result"] == "CONFIRMED")
        falsified = sum(1 for r in calibration_log if r["result"] == "FALSIFIED")
        inconclusive = sum(1 for r in calibration_log if r["result"] == "INCONCLUSIVE")

        # Calibration curve
        curve = self._compute_calibration_curve(calibration_log)

        report = f"""# SELF-AUDIT REPORT -- {self.workspace.name} -- {datetime.now().strftime('%Y-%m-%d')} ({mode.title()} Mode)

## Session Summary
- Mode: {mode}
- Workspace: {self.workspace}
- Cross-model validation: {'Yes' if mode == 'deep' else 'No'}
- Historical trend: {'Loaded' if mode == 'deep' else 'N/A'}

## Assumption Statistics
| Metric | Count |
|--------|-------|
| Total assumptions extracted | {len(assumptions)} |
| Testable | {sum(1 for a in assumptions if a['testable'])} |
| Tested | {len(calibration_log)} |
| Confirmed | {confirmed} |
| Falsified (CALIBRATION_ERROR) | {falsified} |
| Inconclusive | {inconclusive} |

## Calibration Curve
"""
        for band, stats in curve.items():
            report += f"- **{band}**: {stats['actual']:.0%} actual (stated {stats['stated']:.0%}) -- {'Overconfident' if stats['delta'] < -0.1 else 'Underconfident' if stats['delta'] > 0.1 else 'Well calibrated'} ({stats['delta']:+.2f})\n"

        report += "\n## Top Blind Spots (by risk = severity ? layer_weight)\n"
        report += "| Rank | ID | Category | Layer | Severity | Delta | Learning Unit |\n"
        report += "|------|-----|----------|-------|----------|-------|---------------|\n"

        for i, bs in enumerate(blind_spots[:10], 1):
            delta = f"{bs['confidence_delta']:.2f}" if bs['confidence_delta'] else "N/A"
            report += f"| {i} | {bs['id']} | {bs['category']} | {bs['layer']} | {bs['severity']} | {delta} | {bs['learning_unit_id']} |\n"

        if learning_units:
            report += "\n## Learning Units Produced\n"
            for lu in learning_units:
                lu_status = lu.get("status", "VERIFIED")
                report += f"- **{lu['id']}**: {lu['content'].split(chr(10))[2] if len(lu['content'].split(chr(10))) > 2 else 'Learning unit'} ({lu_status})\n"

        report += f"""
## Pre-Load Recommendations for Next Session
1. Load `WORKSPACE_MODEL.md` (updated)
2. Load memory: architecture-pattern (if L3 correction)
3. Load memory: error-handling-convention (if L2 correction)
4. Flag unverified blind spots for early testing

## Stop Reason
**STOP C**: Next useful step is execution.
"""
        # Domain-Adaptive Layer section (v1.3) — appended after existing
        # sections so existing parsers/graders are unaffected.
        stats = getattr(self, "_domain_layer_stats", None)
        if stats:
            report += "\n## Domain-Adaptive Layer\n"
            if mode == "quick":
                report += ("- Findings (top risks): " + str(stats["finding_count"]) + "\n"
                           "- Pattern candidates: skipped (quick depth)\n"
                           "- Blind-spot candidates: " + str(stats["blind_spot_candidate_count"]) + "\n")
            else:
                report += ("- Findings: " + str(stats["finding_count"]) + "\n"
                           "- Pattern candidates (all CANDIDATE — lexical nomination only): "
                           + str(stats["pattern_candidate_count"]) + "\n"
                           "- Blind-spot candidates: " + str(stats["blind_spot_candidate_count"]) + "\n"
                           "- Full detail: analysis-findings.json"
                           + (" and domain-model.md" if mode != "quick" else "") + "\n")
            if stats.get("validation_error_count"):
                report += ("- Validation errors embedded in analysis-findings.json: "
                           + str(stats["validation_error_count"]) + "\n")
        return report

    def _clear_stale_cross_model_log(self):
        """A prior run's cross-model log must never survive into an honest
        NOT_RUN: stale confirmations read as reviews that never happened.
        Called at the start of the phase and on every explicit-disable path."""
        stale = self.knowledge_root / "cross-model-validation.log.jsonl"
        if stale.exists():
            try:
                stale.unlink()
            except OSError as e:
                print(f"    [WARN] could not remove stale cross-model log: {e}", file=sys.stderr)

    def _phase_cross_model_validation(self):
        """Deep mode: Cross-model adversarial validation.

        Honesty contract (v1.3): a review happens only when an external
        reviewer command actually runs and receives the blind-spot payload
        (JSON on stdin). With no reviewer command configured, validation is
        NOT_RUN — no log is written, no reviewer is invented, and the report
        says so. Unparseable output is recorded as UNPARSED and never
        counts as a review.
        """
        print("  Deep: Cross-model validation...")
        validation_log = self.knowledge_root / "cross-model-validation.log.jsonl"
        # Drop any stale log first: every path below either rewrites it from
        # real records or must leave none at all.
        self._clear_stale_cross_model_log()

        specs = self._load_external_reviewers()
        if not specs:
            print("    NOT_RUN: no external reviewer command configured")
            return {"reviewers": 0, "status": "NOT_RUN"}

        # Real blind spots to review (parsed from the register written by
        # Phase 3 this session — never invented)
        blind_spots = self._parse_blind_spot_table()
        if not blind_spots:
            print("    NOT_RUN: no blind spots to review")
            return {"reviewers": 0, "status": "NOT_RUN",
                    "note": "no blind spots to review"}

        records = []
        for bs in blind_spots[:3]:  # review top 3 by risk
            payload = json.dumps({
                "blind_spot_id": bs["id"],
                "category": bs["category"],
                "layer": bs["layer"],
                "severity": bs.get("severity", ""),
                "review_target": {
                    "statement": bs.get("statement", ""),
                    "evidence": bs.get("evidence_summary", ""),
                    "impact": bs.get("impact", ""),
                    "learning_objective": bs.get("learning_objective", ""),
                    "verification_protocol": bs.get("verification_protocol", ""),
                },
                "workspace": str(self.workspace),
                "instruction": "Adversarially verify this blind spot. Reply with a "
                               "single JSON object containing at least "
                               "{\"verdict\": \"CONFIRMED|REFUTED|PARTIAL\"} and "
                               "optional \"notes\", \"additional_blind_spots\".",
            })
            for spec in specs:
                records.append(self._run_external_reviewer(spec, bs, payload))

        # Only parseable verdicts count as reviews; UNPARSED/error records
        # are kept for honesty but excluded from the stats.
        parseable = [r for r in records if r["verdict"] != "UNPARSED"]
        reviewers_with_verdict = len({r["reviewer"] for r in parseable})
        confirmed = sum(1 for r in parseable if r["verdict"] == "CONFIRMED")

        with validation_log.open("w") as f:
            for r in records:
                f.write(json.dumps(r) + "\n")
        print(f"    Cross-model validation: {len(parseable)} parseable review(s) from "
              f"{reviewers_with_verdict} reviewer(s); {len(records) - len(parseable)} "
              f"unparseable/failed record(s)")
        return {
            "status": "RUN",
            "reviewers": reviewers_with_verdict,
            "total_reviews": len(parseable),
            "confirmed": confirmed,
            "agreement_rate": (confirmed / len(parseable)) if parseable else 0.0,
            "unparsed": len(records) - len(parseable),
        }

    def _load_external_reviewers(self) -> List[Dict]:
        """Load reviewer specs from SELF_AUDIT_EXTERNAL_REVIEWERS.

        Format: JSON list of {"name": str, "command": str}. Invalid JSON is
        treated as not configured (with a warning) — never as a silent
        zero-review 'run'."""
        raw = os.getenv("SELF_AUDIT_EXTERNAL_REVIEWERS", "")
        if not raw.strip():
            return []
        try:
            data = json.loads(raw)
        except json.JSONDecodeError as e:
            print(f"    [WARN] SELF_AUDIT_EXTERNAL_REVIEWERS is not valid JSON "
                  f"({e}) — treating as not configured", file=sys.stderr)
            return []
        specs = []
        if isinstance(data, list):
            for item in data:
                if isinstance(item, dict) and item.get("name") and item.get("command"):
                    specs.append({"name": str(item["name"]),
                                  "command": str(item["command"])})
        return specs

    def _parse_blind_spot_table(self) -> List[Dict]:
        """Parse this session's blind-spot register into review targets.

        Combines the risk table (id/category/layer/severity) with the
        detail sections (assumption, evidence, impact, learning objective,
        verification protocol) so a reviewer command receives the full
        review target — an ID alone cannot substantively verify anything.
        """
        blind_spots_path = self.knowledge_root / "blind-spots.md"
        blind_spots: List[Dict] = []
        if not blind_spots_path.exists():
            return blind_spots
        content = blind_spots_path.read_text(encoding="utf-8", errors="ignore")
        table_match = re.search(
            r'\| Rank \| ID \| Category \| Layer \| Severity \| Delta \| Learning Unit \|\n\|.*?\n((?:\|.*?\n)*)',
            content)
        if table_match:
            rows = table_match.group(1).strip().split('\n')
            for row in rows:
                parts = [p.strip() for p in row.split('|')[1:-1]]
                if len(parts) >= 7:
                    blind_spots.append({
                        "id": parts[1],
                        "category": parts[2],
                        "layer": parts[3],
                        "severity": parts[4],
                    })
        if not blind_spots:
            return blind_spots

        # Detail blocks: "### BS-001 -- Critical L3 CATEGORY" followed by
        # bold-field lines (see _format_blind_spots)
        detail_re = re.compile(
            r"### (\S+) -- [^\n]*\n(.*?)(?=\n### |\Z)", re.DOTALL)
        field_re = re.compile(r"^- \*\*(.+?)\*\*: (.*)$", re.MULTILINE)
        details_by_id: Dict[str, Dict[str, str]] = {}
        for m in detail_re.finditer(content):
            fields = {}
            for fm in field_re.finditer(m.group(2)):
                fields[fm.group(1).strip().lower()] = fm.group(2).strip()
            details_by_id[m.group(1)] = fields
        for bs in blind_spots:
            fields = details_by_id.get(bs["id"], {})
            bs["statement"] = fields.get("assumption", "")
            bs["evidence_summary"] = fields.get("evidence", "")
            bs["impact"] = fields.get("impact", "")
            bs["learning_objective"] = fields.get("learning objective", "")
            bs["verification_protocol"] = fields.get("verification protocol", "")
        return blind_spots

    def _run_external_reviewer(self, spec: Dict, bs: Dict, payload: str) -> Dict:
        """Run one reviewer command against one blind-spot payload (stdin).

        The record carries the REAL command, exit code, and captured output
        — the verdict is parsed from stdout only; a failing or silent
        reviewer is recorded, never invented."""
        import subprocess
        record = {
            "blind_spot_id": bs["id"],
            "reviewer": spec["name"],
            "command": spec["command"],
            "exit_code": None,
            "verdict": "UNPARSED",
            "notes": "",
            "additional_blind_spots": [],
            "stdout_excerpt": "",
            "error": None,
            "timestamp": datetime.now().isoformat(),
        }
        try:
            result = subprocess.run(
                spec["command"], shell=True, input=payload,
                capture_output=True, text=True, timeout=300)
            record["exit_code"] = result.returncode
            record["stdout_excerpt"] = (result.stdout or "")[-500:]
            if result.stderr:
                record["error"] = result.stderr[:200]
            # Honesty gate: a verdict is parsed ONLY from a successful run.
            # A command that prints valid JSON but exits non-zero failed —
            # its output is recorded as an excerpt, never counted as a review.
            if result.returncode == 0:
                verdict, notes, additional = self._parse_reviewer_output(result.stdout or "")
                if verdict is not None:
                    record["verdict"] = verdict
                    record["notes"] = str(notes or "")
                    record["additional_blind_spots"] = list(additional or [])
            else:
                record["verdict"] = "UNPARSED"
                if not record["error"]:
                    record["error"] = f"reviewer command exited {result.returncode}"
        except subprocess.TimeoutExpired:
            record["error"] = "timeout after 300s"
        except (OSError, ValueError) as e:
            record["error"] = f"execution failed: {e}"
        return record

    def _parse_reviewer_output(self, stdout: str):
        """Parse the last JSON object with a 'verdict' key from reviewer
        stdout. Returns (verdict, notes, additional_blind_spots) or
        (None, None, None) when nothing parses."""
        for line in reversed((stdout or "").strip().splitlines()):
            line = line.strip().rstrip(",")
            if not line.startswith("{"):
                continue
            try:
                obj = json.loads(line)
            except json.JSONDecodeError:
                continue
            if isinstance(obj, dict) and isinstance(obj.get("verdict"), str) and obj["verdict"]:
                return obj["verdict"], obj.get("notes"), obj.get("additional_blind_spots")
        return None, None, None

    def _phase_trend_analysis(self):
        """Deep mode: Historical trend analysis."""
        print("  Deep: Historical trend analysis...")
        log_path = self.knowledge_root / "calibration.log.jsonl"
        if log_path.exists():
            lines = log_path.read_text().strip().split("\n")
            print(f"    Analyzed {len(lines)} calibration records")
            # Produce trend report
            return self._write_trend_report(log_path)
        else:
            print("    No prior calibration history")
            return None

    def _write_trend_report(self, log_path: Path):
        """Generate calibration trend report."""
        import json
        records = []
        with open(log_path) as f:
            for line in f:
                line = line.strip()
                if line:
                    records.append(json.loads(line))

        if not records:
            return

        # Group by session
        sessions = {}
        for r in records:
            sid = r.get("session_id", "unknown")
            if sid not in sessions:
                sessions[sid] = {"deltas": [], "falsified": 0, "confirmed": 0, "count": 0, "layers": {}}
            sessions[sid]["count"] += 1
            delta = abs(r.get("confidence_delta", 0))
            sessions[sid]["deltas"].append(delta)
            if r.get("result") == "FALSIFIED":
                sessions[sid]["falsified"] += 1
            elif r.get("result") == "CONFIRMED":
                sessions[sid]["confirmed"] += 1
            layer = r.get("layer", "L1")
            if layer not in sessions[sid]["layers"]:
                sessions[sid]["layers"][layer] = []
            sessions[sid]["layers"][layer].append(delta)

        # Compute metrics (session gate configurable via SELF_AUDIT_TREND_MIN_SESSIONS)
        session_ids = sorted(sessions.keys())
        if len(session_ids) >= self.trend_min_sessions:
            first_sid = session_ids[0]
            last_sid = session_ids[-1]
            first_mean = sum(sessions[first_sid]["deltas"]) / len(sessions[first_sid]["deltas"]) if sessions[first_sid]["deltas"] else 0
            last_mean = sum(sessions[last_sid]["deltas"]) / len(sessions[last_sid]["deltas"]) if sessions[last_sid]["deltas"] else 0
            trend = "IMPROVING" if last_mean < first_mean else "DEGRADING" if last_mean > first_mean else "STABLE"
        else:
            trend = "INSUFFICIENT_DATA"

        # Overall calibration
        # Keep the sign: a negative delta = overconfident (stated > actual),
        # a positive delta = underconfident. abs() is only for magnitude stats.
        signed_deltas = [r.get("confidence_delta", 0) for r in records]
        all_deltas = [abs(d) for d in signed_deltas]
        mean_delta = sum(all_deltas) / len(all_deltas) if all_deltas else 0
        overconfident = sum(1 for d in signed_deltas if d < -0.3)
        underconfident = sum(1 for d in signed_deltas if d > 0.3)
        overconf_rate = overconfident / len(records) if records else 0
        underconf_rate = underconfident / len(records) if records else 0

        # By layer
        layer_metrics = {}
        for layer in ["L1", "L2", "L3", "L4"]:
            layer_deltas = [abs(r.get("confidence_delta", 0)) for r in records if r.get("layer") == layer]
            if layer_deltas:
                layer_metrics[layer] = sum(layer_deltas) / len(layer_deltas)

        # Write report
        report = f"""# CALIBRATION TREND REPORT -- {self.workspace.name} -- {datetime.now().strftime('%Y-%m-%d')}

## Sessions Analyzed: {len(session_ids)}

## Overall Calibration
- Mean |delta|: {mean_delta:.2f}
- Overconfidence rate: {overconf_rate:.0%}
- Underconfidence rate: {underconf_rate:.0%}
- Trend: {trend}

## By Layer
| Layer | Mean |delta| |
|-------|------|
"""
        for layer, val in sorted(layer_metrics.items()):
            report += f"| {layer} | {val:.2f} |\n"

        report += f"""
## Persistent Weak Spots
"""
        # Find recurring patterns
        if records:
            falsified_by_category = {}
            for r in records:
                if r.get("result") == "FALSIFIED":
                    cat = r.get("new_status", "UNKNOWN")
                    falsified_by_category[cat] = falsified_by_category.get(cat, 0) + 1
            for cat, count in sorted(falsified_by_category.items(), key=lambda x: -x[1]):
                report += f"- **{cat}** -- Recurring in {count} records\n"

        report += f"""
## Recommendations
- Review calibration errors in L3/L4 assumptions
- Add verified conventions to memory
- Continue tracking calibration across sessions
"""

        trend_path = self.knowledge_root / "calibration-trend-report.md"
        trend_path.write_text(report)
        print(f"    Trend report written to {trend_path}")

        return {
            "sessions": len(session_ids),
            "mean_delta": mean_delta,
            "overconfident_rate": overconf_rate,
            "underconfident_rate": underconf_rate,
            "trend": trend,
            "records": len(records),
        }

    def _update_report_for_deep_mode(self, cross_model_stats=None, trend_stats=None):
        """Update calibration report with real deep mode findings (no fabricated metrics)."""
        report_path = self.knowledge_root / "calibration-report.md"
        if not report_path.exists():
            return
        content = report_path.read_text()
        content = content.replace("(Quick Mode)", "(Deep Mode)").replace("(Standard Mode)", "(Deep Mode)")

        # Cross-model section — honest NOT_RUN vs real reviewer counts.
        # "None" = explicitly disabled; status NOT_RUN = no reviewer configured.
        content += "\n## Cross-Model Validation\n"
        if cross_model_stats and cross_model_stats.get("status") == "RUN":
            content += (f"- Reviewers with parseable verdicts: {cross_model_stats['reviewers']}\n"
                        f"- Reviews: {cross_model_stats['total_reviews']}\n"
                        f"- Confirmed verdicts: {cross_model_stats['confirmed']}\n"
                        f"- Agreement rate: {cross_model_stats['agreement_rate']:.0%}\n")
            if cross_model_stats.get("unparsed"):
                content += (f"- Unparseable/failed reviewer records: "
                            f"{cross_model_stats['unparsed']} (recorded, not counted)\n")
        elif cross_model_stats is None:
            content += ("- NOT_RUN: explicitly disabled (via --no-cross-model or "
                        "SELF_AUDIT_CROSS_MODEL=false) — no reviews exist for this run\n")
        else:
            if cross_model_stats.get("note") == "no blind spots to review":
                content += ("- NOT_RUN: no blind spots to review this session "
                            "(reviewer commands configured but had nothing to review) "
                            "— no reviews exist for this run\n")
            else:
                content += ("- NOT_RUN: no external reviewer command configured "
                            "(set SELF_AUDIT_EXTERNAL_REVIEWERS; see docs) "
                            "— no reviews exist for this run\n")

        # Trend section from real stats
        content += "\n## Calibration Trend\n"
        if trend_stats:
            content += (f"- Sessions tracked: {trend_stats['sessions']} ({trend_stats['records']} records)\n"
                        f"- Mean |delta|: {trend_stats['mean_delta']:.2f}\n"
                        f"- Overconfidence rate: {trend_stats['overconfident_rate']:.0%}\n"
                        f"- Underconfidence rate: {trend_stats['underconfident_rate']:.0%}\n"
                        f"- Trend: {trend_stats['trend']}\n")
        else:
            content += "- Not run (trend analysis disabled or insufficient history)\n"

        report_path.write_text(content)


    def _write_domain_layer_artifacts(self, mode: str, workspace_model: Dict,
                                       assumptions: List[Dict],
                                       calibration_log: List[Dict],
                                       blind_spots: List[Dict],
                                       learning_units: List[Dict],
                                       depth: Dict) -> None:
        """Write analysis-findings.json (+ domain-model.md at standard+).

        Every written report passes domain_analysis.validate_analysis_report;
        validation errors are printed to stderr and embedded in the file
        under 'validation_errors' — fail visible, never silent.
        """
        task_resolution = self._phase_0_6_task_resolution(workspace_model)
        domain_model = None
        if depth.get("domain_model"):
            domain_model = self._phase_0_7_domain_model(workspace_model)

        # Findings derive from blind spots (real falsifications) — each
        # carries the calibration record's evidence, never invented.
        findings = []
        for i, bs in enumerate(blind_spots[:5], 1):
            statement = bs.get("assumption_statement") or bs.get("evidence_summary", "")
            findings.append({
                "id": f"FIND-{i:03d}",
                "statement": str(statement)[:300],
                "category_path": f"calibration.{str(bs.get('category', 'blind-spot')).lower()[:40]}",
                "layer": bs.get("layer", "L2"),
                "evidence_status": "OBSERVED" if bs.get("evidence_summary") else "UNVERIFIED_CLAIM",
                "source_refs": [],
                "evidence_scope": "derived from this session's calibration log "
                                  "(falsified assumption records)",
                "confidence_band": "HIGH" if bs.get("severity") == "Critical" else "MEDIUM",
                "uncertainty_reason": "finding derived from a falsified assumption; "
                                      "corrected belief recorded in the blind-spot register"
                if bs.get("evidence_summary") else "no evidence recorded for this blind spot",
                "related_findings": [],
                "verification_method": "static_analysis",
                "verification_status": "NOT_RUN",
            })

        # Uncertainty findings from INCONCLUSIVE load-bearing records
        for r in calibration_log:
            if r.get("result") == "INCONCLUSIVE" and r.get("layer") in ("L3", "L4") \
                    and len(findings) < 10:
                findings.append({
                    "id": f"FIND-{len(findings) + 1:03d}",
                    "statement": f"Unresolved: {r.get('prediction', '')[:250]}",
                    "category_path": "calibration.unresolved",
                    "layer": r.get("layer", "L3"),
                    "evidence_status": "UNVERIFIED_CLAIM",
                    "source_refs": [str(e) for e in (r.get("evidence") or [])][:5],
                    "evidence_scope": r.get("inconclusive_reason", "check ran but was inconclusive"),
                    "confidence_band": "LOW",
                    "uncertainty_reason": r.get("inconclusive_reason",
                                                "check could not settle the claim"),
                    "related_findings": [],
                    "verification_method": r.get("verification_method", "static_analysis"),
                    "verification_status": "RUN",
                })

        patterns = []
        if depth.get("pattern_discovery"):
            nominated = self._phase_2_5_pattern_candidates(calibration_log)
            # Candidates keep their member_assumption_ids (real ASSUME-ids);
            # to satisfy the pattern schema they anchor to this report's
            # findings via member_finding_ids when findings exist.
            for p in nominated:
                if not findings:
                    break
                p["member_finding_ids"] = [findings[0]["id"]]
                p.pop("member_assumption_ids", None)
                p["verification_status"] = "NOT_RUN"
                patterns.append(p)

        blind_spot_candidates = self._phase_3_5_blind_spot_search(
            workspace_model, assumptions, calibration_log)

        report: Dict[str, Any] = {
            "schema_version": domain_analysis.SCHEMA_VERSION,
            "subject": f"{self.workspace.name} ({self.target})",
            "task_resolution": task_resolution,
            "findings": findings,
            "blind_spot_candidates": blind_spot_candidates,
            "scope": {
                "inspected": [str(p) for p in workspace_model.get("structure", {}).get("config_files", [])][:10]
                             + [f"{d}" for d in workspace_model.get("structure", {}).get("source_dirs", [])[:10]],
                "not_inspected": ["areas outside the workspace root",
                                  "generated/vendored content semantics"],
                "note": "not-found means not found under the stated scope, never does-not-exist",
            },
        }
        if domain_model is not None:
            report["domain_model"] = domain_model
        if patterns:
            report["patterns"] = patterns

        # Validate; embed errors visibly rather than silently writing garbage.
        errors = domain_analysis.validate_analysis_report(report)
        if errors:
            print(f"    [DOMAIN-LAYER] {len(errors)} validation error(s) — "
                  f"embedded in analysis-findings.json", file=sys.stderr)
            for e in errors[:5]:
                print(f"        - {e}", file=sys.stderr)
            report["validation_errors"] = errors

        self._write_json(self.knowledge_root / "analysis-findings.json", report)
        if domain_model is not None:
            self._write_markdown(
                self.knowledge_root / "domain-model.md",
                self._format_domain_model_md(domain_model))

        # Stash counts for the summary + report sections.
        self._domain_layer_stats = {
            "domain_layer": True,
            "finding_count": len(findings),
            "pattern_candidate_count": len(patterns),
            "blind_spot_candidate_count": len(blind_spot_candidates),
            "validation_error_count": len(errors),
        }
        print(f"    [DOMAIN-LAYER] analysis-findings.json: {len(findings)} findings, "
              f"{len(patterns)} pattern candidates, "
              f"{len(blind_spot_candidates)} blind-spot candidates"
              + (f" ({len(errors)} validation errors)" if errors else ""))

    def _format_domain_model_md(self, domain_model: Dict) -> str:
        """Render the domain model as markdown (template-compatible)."""
        md = f"# DOMAIN_MODEL — {domain_model.get('subject', self.workspace.name)} — "
        md += f"{datetime.now().strftime('%Y-%m-%d')}\n\n"
        md += "## Concepts\n\n"
        md += "| Concept | Definition | Distinguishing criteria (vs) | Status |\n"
        md += "|---------|------------|------------------------------|--------|\n"
        for c in domain_model.get("concepts", []):
            name = c.get("name", "")
            definition = c.get("definition", "").replace("|", "\\|")[:120]
            distinguishes = "; ".join(
                f"{d.get('criterion', '')} vs {d.get('vs_concept', '')}"
                for d in c.get("distinguishes", [])) or "— (agent fills: criteria not yet derived)"
            status = c.get("status", "PROPOSED")
            md += f"| {name} | {definition} | {distinguishes} | {status} |\n"
        md += "\n## Coverage Notes\n\n"
        notes = domain_model.get("coverage_notes", "")
        if isinstance(notes, list):
            for n in notes:
                md += f"- {n}\n"
        else:
            md += f"- {notes}\n"
        md += "\n*PROPOSED concepts are provisional and require verification — "
        md += "never present a constructed category as established knowledge.*\n"
        return md

    # ===== HELPER METHODS =====

    def _detect_domain(self) -> str:
        """Detect project domain from files."""
        # Check for domain indicators
        indicators = {
            "web": ["package.json", "tsconfig.json", "vite.config.ts"],
            "python": ["pyproject.toml", "requirements.txt", "setup.py"],
            "go": ["go.mod", "go.sum"],
            "rust": ["Cargo.toml", "Cargo.lock"],
            "java": ["pom.xml", "build.gradle"],
            "mobile": ["pubspec.yaml", "Podfile", "build.gradle.kts"],
        }
        for domain, files in indicators.items():
            if any((self.workspace / f).exists() for f in files):
                return domain
        return "general"

    def _detect_stack(self) -> Dict:
        """Detect tech stack."""
        stack = {"languages": [], "frameworks": [], "build_tools": [], "test_runners": [], "linters": [], "type_checkers": []}

        # Language detection — manifest files first (high signal)...
        if (self.workspace / "pyproject.toml").exists() or (self.workspace / "requirements.txt").exists():
            stack["languages"].append("Python")
        if (self.workspace / "package.json").exists():
            stack["languages"].append("TypeScript/JavaScript")
        if (self.workspace / "go.mod").exists():
            stack["languages"].append("Go")
        if (self.workspace / "Cargo.toml").exists():
            stack["languages"].append("Rust")

        # ...then by file-extension scan, so Java/C#/PHP/Ruby/Kotlin/Swift etc.
        # are detected even without a familiar manifest file.
        ext_langs = self._detect_languages()
        for lang, info in ext_langs.items():
            if info["label"] not in stack["languages"]:
                stack["languages"].append(f"{info['label']} ({info['file_count']} files)")

        # Framework detection (simplified)
        if (self.workspace / "pyproject.toml").exists():
            content = (self.workspace / "pyproject.toml").read_text()
            if "fastapi" in content.lower(): stack["frameworks"].append("FastAPI")
            if "django" in content.lower(): stack["frameworks"].append("Django")
            if "pytest" in content.lower(): stack["test_runners"].append("pytest")
            if "mypy" in content.lower(): stack["type_checkers"].append("mypy")
            if "ruff" in content.lower(): stack["linters"].append("ruff")

        if (self.workspace / "package.json").exists():
            content = (self.workspace / "package.json").read_text()
            if "next" in content.lower(): stack["frameworks"].append("Next.js")
            if "react" in content.lower(): stack["frameworks"].append("React")
            if "jest" in content.lower(): stack["test_runners"].append("Jest")
            if "eslint" in content.lower(): stack["linters"].append("ESLint")
            if "typescript" in content.lower(): stack["type_checkers"].append("TypeScript")

        return stack

    def _inventory_structure(self) -> Dict:
        """Inventory workspace structure."""
        structure = {"source_dirs": [], "test_dirs": [], "config_files": [], "doc_dirs": [], "memory_dirs": [], "claude_files": []}

        for item in self.workspace.rglob("*"):
            if item.is_dir():
                rel = item.relative_to(self.workspace)
                parts = rel.parts
                if parts[0] in ("src", "lib", "app", "source"):
                    structure["source_dirs"].append(str(rel))
                elif parts[0] in ("test", "tests", "spec", "specs"):
                    structure["test_dirs"].append(str(rel))
                elif parts[0] == ".claude":
                    structure["claude_files"].append(str(rel))
                    if "memory" in parts:
                        structure["memory_dirs"].append(str(rel))
            elif item.is_file():
                rel = item.relative_to(self.workspace)
                if item.suffix in (".yaml", ".yml", ".json", ".toml", ".ini", ".conf", ".config"):
                    structure["config_files"].append(str(rel))
                elif item.suffix in (".md", ".rst", ".txt") and "doc" in str(rel).lower():
                    structure["doc_dirs"].append(str(rel.parent))

        # Deduplicate
        for key in structure:
            structure[key] = list(set(structure[key]))[:20]  # Limit

        return structure

    # ---- Language profiles for multi-language convention detection ----
    # Each language maps file extensions to its id, and a set of regex patterns
    # that capture its idiomatic conventions (error handling, tests, etc.).
    _LANGUAGE_PROFILES = {
        "python": {
            "label": "Python",
            "extensions": [".py"],
            "error_pattern": r"\btry\s*:",
            "test_globs": ["test_*.py", "*_test.py"],
            "test_marker": None,
        },
        "typescript": {
            "label": "TypeScript/JavaScript",
            "extensions": [".ts", ".tsx", ".js", ".jsx", ".mjs", ".cjs"],
            "error_pattern": r"\bcatch\s*\(",
            "test_globs": ["*.test.ts", "*.test.tsx", "*.test.js", "*.spec.ts", "*.spec.js"],
            "test_marker": None,
        },
        "go": {
            "label": "Go",
            "extensions": [".go"],
            "error_pattern": r"if\s+err\s*!=\s*nil",
            "test_globs": ["*_test.go"],
            "test_marker": None,
        },
        "rust": {
            "label": "Rust",
            "extensions": [".rs"],
            "error_pattern": r"->\s*Result<|\.unwrap\(\)|\bmatch\s+.*\{",
            "test_globs": [],
            "test_marker": "#[test]",
        },
        "java": {
            "label": "Java",
            "extensions": [".java"],
            "error_pattern": r"\bcatch\s*\(",
            "test_globs": [],
            "test_marker": "@Test",
        },
        "kotlin": {
            "label": "Kotlin",
            "extensions": [".kt", ".kts"],
            "error_pattern": r"\bcatch\s*\(",
            "test_globs": [],
            "test_marker": "@Test",
        },
        "csharp": {
            "label": "C#",
            "extensions": [".cs"],
            "error_pattern": r"\bcatch\s*\(",
            "test_globs": [],
            "test_marker": "[Test]",
        },
        "ruby": {
            "label": "Ruby",
            "extensions": [".rb"],
            "error_pattern": r"\brescue\b",
            "test_globs": ["*_spec.rb", "*_test.rb"],
            "test_marker": None,
        },
        "php": {
            "label": "PHP",
            "extensions": [".php"],
            "error_pattern": r"\bcatch\s*\(",
            "test_globs": ["*Test.php"],
            "test_marker": None,
        },
        "swift": {
            "label": "Swift",
            "extensions": [".swift"],
            "error_pattern": r"\bdo\s*\{|\bthrows\b|\btry\b",
            "test_globs": [],
            "test_marker": "func test",
        },
    }

    def _detect_languages(self) -> Dict[str, Dict]:
        """Detect present languages by file-extension scan (not just manifest files)."""
        found = {}
        # Count files per language extension
        for lang, profile in self._LANGUAGE_PROFILES.items():
            count = 0
            for ext in profile["extensions"]:
                count += len(list(self.workspace.rglob(f"*{ext}")))
            if count > 0:
                found[lang] = {"label": profile["label"], "file_count": count}
        return found

    def _sample_conventions(self) -> List[Dict]:
        """Sample high-signal conventions across all detected languages."""
        conventions = []

        # Config convention (language-neutral)
        cfg_evidence = []
        yaml_count = json_count = toml_count = 0
        for f in self.workspace.rglob("*"):
            if not f.is_file() or any(part in self._SCAN_SKIP_DIRS for part in f.relative_to(self.workspace).parts):
                continue
            if f.suffix in (".yaml", ".yml"):
                yaml_count += 1
            elif f.suffix == ".json":
                json_count += 1
            elif f.suffix == ".toml":
                toml_count += 1
            else:
                continue
            if len(cfg_evidence) < 5:
                cfg_evidence.append(f.relative_to(self.workspace).as_posix())
        cfg_total = yaml_count + json_count + toml_count
        if cfg_total > 0:
            dominant = "YAML" if yaml_count >= json_count and yaml_count >= toml_count else "JSON" if json_count >= toml_count else "TOML"
            conventions.append({
                "pattern": f"config files use {dominant} (yaml={yaml_count}, json={json_count}, toml={toml_count})",
                "frequency": cfg_total,
                "exceptions": [],
                "status": "UNVERIFIED_PATTERN",
                "evidence_files": cfg_evidence
            })

        # Per-language convention sampling
        for lang, profile in self._LANGUAGE_PROFILES.items():
            exts = profile["extensions"]
            # --- error handling idiom ---
            err_hits = 0
            err_files = []
            for f in self.workspace.rglob("*"):
                if f.is_file() and f.suffix in exts:
                    try:
                        content = f.read_text(encoding="utf-8", errors="ignore")
                        hits = len(re.findall(profile["error_pattern"], content))
                        if hits:
                            err_hits += hits
                            if len(err_files) < 3:
                                err_files.append(str(f.relative_to(self.workspace)))
                    except Exception:
                        pass
            if err_hits > 0:
                conventions.append({
                    "pattern": f"{profile['label']} error handling idiom",
                    "frequency": err_hits,
                    "exceptions": [],
                    "status": "UNVERIFIED_PATTERN",
                    "evidence_files": err_files
                })

            # --- test naming / marker convention ---
            test_files = 0
            test_evidence = []
            for glob in profile["test_globs"]:
                for f in self.workspace.rglob(glob):
                    if any(part in self._SCAN_SKIP_DIRS for part in f.relative_to(self.workspace).parts):
                        continue
                    test_files += 1
                    if len(test_evidence) < 5:
                        test_evidence.append(f.relative_to(self.workspace).as_posix())
            if profile["test_marker"]:
                for f in self.workspace.rglob("*"):
                    if f.is_file() and f.suffix in exts:
                        try:
                            if profile["test_marker"] in f.read_text(encoding="utf-8", errors="ignore"):
                                test_files += 1
                                if len(test_evidence) < 5:
                                    test_evidence.append(f.relative_to(self.workspace).as_posix())
                        except Exception:
                            pass
            if test_files > 0:
                conventions.append({
                    "pattern": f"{profile['label']} test convention",
                    "frequency": test_files,
                    "exceptions": [],
                    "status": "UNVERIFIED_PATTERN",
                    "evidence_files": test_evidence
                })

        return conventions

    def _load_memory_index(self) -> List[Dict]:
        """Load existing memory index."""
        memories = []
        memory_dir = self.workspace / ".claude" / "projects"
        if memory_dir.exists():
            for mem_file in memory_dir.rglob("MEMORY.md"):
                try:
                    content = mem_file.read_text()
                    for line in content.split("\n"):
                        if line.startswith("- [") and "](" in line:
                            name = line.split("[")[1].split("]")[0]
                            memories.append({"name": name, "description": "Memory entry", "layer": "L3", "verified": True, "calibration_delta": 0.0})
                except:
                    pass
        return memories

    def _load_calibration_history(self) -> List[Dict]:
        """Load calibration history."""
        history = []
        log_path = self.knowledge_root / "calibration.log.jsonl"
        if log_path.exists():
            # Group by session
            sessions = {}
            for line in log_path.read_text().strip().split("\n"):
                if line.strip():
                    try:
                        record = json.loads(line)
                        sid = record.get("session_id", "unknown")
                        if sid not in sessions:
                            sessions[sid] = {"count": 0, "confirmed": 0, "falsified": 0, "deltas": []}
                        sessions[sid]["count"] += 1
                        if record.get("result") == "CONFIRMED":
                            sessions[sid]["confirmed"] += 1
                        if record.get("result") == "FALSIFIED":
                            sessions[sid]["falsified"] += 1
                        sessions[sid]["deltas"].append(abs(record.get("confidence_delta", 0)))
                    except:
                        pass

            for sid, data in sessions.items():
                history.append({
                    "session_id": sid,
                    "total_assumptions": data["count"],
                    "confirmed_count": data["confirmed"],
                    "falsified_count": data["falsified"],
                    "mean_delta": sum(data["deltas"]) / len(data["deltas"]) if data["deltas"] else 0
                })
        return history

    # ===== PHASE 2 REAL CHECKS =====
    # Every outcome below is grounded in an observation made during THIS run:
    # a real path, a real count, a real directory inventory. When no decisive
    # check is available the record is honestly INCONCLUSIVE (check_status
    # BLOCKED when an environment constraint caused it). Simulated outcomes and
    # fabricated evidence paths are banned (Anti-Pattern #11, §4 negative search).

    _SCAN_SKIP_DIRS = {".git", ".claude", "node_modules", "__pycache__", "dist",
                       "build", ".venv", "venv", ".tox", ".mypy_cache", ".pytest_cache"}

    def _iter_text_files(self, suffixes: Optional[set] = None):
        """Bounded, read-only file walk. Yields (Path, text) with real content."""
        for f in sorted(self.workspace.rglob("*")):
            try:
                if not f.is_file():
                    continue
                rel_parts = f.relative_to(self.workspace).parts
                if any(part in self._SCAN_SKIP_DIRS for part in rel_parts):
                    continue
                if suffixes and f.suffix not in suffixes:
                    continue
                if f.stat().st_size > 1_000_000:
                    continue
                yield f, f.read_text(encoding="utf-8", errors="ignore")
            except OSError:
                continue

    def _search_scope(self, file_types: Any, paths: Optional[List[str]] = None) -> Dict:
        """Recorded search scope for a scan (§4: every search states its scope)."""
        return {
            "paths": paths or ["."],
            "ignore_rules": "default (skips .git/.claude/node_modules/__pycache__/dist/build/venv)",
            "case_sensitive": False,
            "file_types": sorted(file_types) if isinstance(file_types, (set, list)) else file_types,
        }

    def _scan_docs_for(self, phrase: str) -> List[str]:
        """Search *.md content for a phrase; returns real path:line hits."""
        hits: List[str] = []
        for f, text in self._iter_text_files(suffixes={".md"}):
            for i, line in enumerate(text.splitlines(), 1):
                if re.search(phrase, line, re.IGNORECASE):
                    hits.append(f"{f.relative_to(self.workspace).as_posix()}:{i}")
                    if len(hits) >= 5:
                        return hits
        return hits

    def _test_assumption(self, assumption: Dict) -> Dict:
        """Test a single assumption with real, deterministic workspace checks."""
        stated = float(assumption.get("confidence", 0.5))
        if assumption.get("type") == "USER_CONTEXT":
            result = self._test_user_context_assumption(assumption)
        elif assumption.get("type") == "CONVENTION":
            result = self._test_convention_assumption(assumption)
        elif assumption.get("type") == "ARCHITECTURAL":
            result = self._test_architectural_assumption(assumption)
        else:  # DOMAIN and anything else: doc-evidence cross-reference
            result = self._test_domain_assumption(assumption)

        # Principled confidence delta (§2): outcome accuracy minus the stated
        # confidence. Unmeasured outcomes (INCONCLUSIVE) carry no update.
        accuracy = {"CONFIRMED": 1.0, "FALSIFIED": 0.0}.get(result["result"])
        result["confidence_delta"] = round(accuracy - stated, 2) if accuracy is not None else 0.0
        result.setdefault("check_status", "RAN")
        result.setdefault("commands_ran", [])
        result.setdefault("commands_assumed", [])
        result.setdefault("search_scope", None)
        return {
            "assumption_id": assumption["id"],
            "timestamp": datetime.now().isoformat(),
            "prediction": assumption["statement"],
            "actual": result.pop("actual"),
            "evidence": result.pop("evidence"),
            "result": result.pop("result"),
            "new_status": result.pop("new_status"),
            "layer": assumption["layer"],
            "stated_confidence": stated,
            "session_id": self.session_id,
            **result,
        }

    def _test_convention_assumption(self, assumption: Dict) -> Dict:
        """Re-derive the convention from the workspace and compare with the
        recorded observation. Statement: 'All {pattern} follow the observed
        pattern' — its falsifier is a file violating the pattern, so a complete
        recount that finds none of the pattern falsifies; count drift alone is
        reported, not punished."""
        statement = assumption["statement"]
        prefix, suffix = "All ", " follow the observed pattern"
        pattern = statement[len(prefix):-len(suffix)] if statement.startswith(prefix) and statement.endswith(suffix) else statement
        recorded = 0
        m = re.search(r"frequency (\d+)", assumption.get("source_evidence", ""))
        if m:
            recorded = int(m.group(1))

        current = {c["pattern"]: c for c in self._sample_conventions()}.get(pattern)
        scope = self._search_scope({".yaml", ".yml", ".json", ".toml", ".py", ".ts", ".js", ".go", ".rs", ".java"})
        if not current or current["frequency"] == 0:
            return {
                "actual": f"Pattern rescan found zero occurrences of '{pattern}' (recorded frequency {recorded})",
                "evidence": [],
                "result": "FALSIFIED",
                "new_status": "CALIBRATION_ERROR",
                "verification_method": "static_analysis",
                "search_scope": scope,
                "corrected_belief": f"'{pattern}' is no longer observed in this workspace; the recorded frequency {recorded} was stale",
            }
        drift = "" if current["frequency"] == recorded else f" (recorded {recorded}; drift noted)"
        return {
            "actual": f"Pattern re-observed at frequency {current['frequency']}{drift}",
            "evidence": list(current.get("evidence_files", [])),
            "result": "CONFIRMED",
            "new_status": "WORKSPACE_CONVENTION",
            "verification_method": "static_analysis",
            "search_scope": scope,
        }

    def _test_architectural_assumption(self, assumption: Dict) -> Dict:
        """Complete, bounded structural inventory — a closed-set observation of
        every top-level and src-level directory, plus scoped doc cross-reference.
        A structural inventory that contradicts the claim is positive evidence;
        absence alone never falsifies (§4 negative-search discipline)."""
        lowered = assumption["statement"].lower()
        dirs = []
        for root in (self.workspace, self.workspace / "src"):
            if root.is_dir():
                dirs += [p for p in root.iterdir()
                         if p.is_dir() and not p.name.startswith(".") and p.name not in self._SCAN_SKIP_DIRS]
        dir_names = {d.name.lower() for d in dirs}
        inv = ", ".join(sorted(f"{d.relative_to(self.workspace).as_posix()}/" for d in dirs)) or "(no subdirectories)"
        scope = self._search_scope("directories", paths=[".", "src/"])

        layer_names = {"domain", "application", "app", "infrastructure", "infra",
                       "presentation", "ui", "interfaces"}
        core_names = {"core", "shared", "common", "kernel"}
        service_names = {"services", "service", "microservices", "workers"}

        if "clean architecture" in lowered or "layered architecture" in lowered or "strict boundaries" in lowered:
            found = sorted(dir_names & layer_names)
            if len(found) >= 2 and dir_names & {"domain", "infrastructure", "infra"}:
                return {
                    "actual": f"Layer directories present: {', '.join(found)}",
                    "evidence": [f"{d.relative_to(self.workspace).as_posix()}/" for d in dirs if d.name.lower() in found],
                    "result": "CONFIRMED",
                    "new_status": "WORKSPACE_CONVENTION",
                    "verification_method": "static_analysis",
                    "search_scope": scope,
                }
            return {
                "actual": f"Complete directory inventory shows no layer separation: {inv}",
                "evidence": [f"{d.relative_to(self.workspace).as_posix()}/" for d in dirs[:5]],
                "result": "FALSIFIED",
                "new_status": "CALIBRATION_ERROR",
                "verification_method": "static_analysis",
                "search_scope": scope,
                "corrected_belief": f"Workspace layout is flat/single-root ({inv}), not layered with strict boundaries; no domain/infrastructure layer directories exist",
            }

        if "modular monolith" in lowered:
            if dir_names & service_names:
                return {
                    "actual": f"Service decomposition directories found: {', '.join(sorted(dir_names & service_names))}",
                    "evidence": [f"{d.relative_to(self.workspace).as_posix()}/" for d in dirs if d.name.lower() in service_names],
                    "result": "FALSIFIED",
                    "new_status": "CALIBRATION_ERROR",
                    "verification_method": "static_analysis",
                    "search_scope": scope,
                    "corrected_belief": "Workspace has service decomposition directories; it is not a modular monolith",
                }
            # Confirm requires a structural core marker — prose is not behavior
            # (Phase 0.5), so doc mentions alone never confirm.
            if dir_names & core_names:
                evidence = [f"{d.relative_to(self.workspace).as_posix()}/" for d in dirs if d.name.lower() in core_names]
                return {
                    "actual": f"Modular-monolith structural evidence found ({', '.join(evidence)}); no service decomposition in inventory",
                    "evidence": evidence,
                    "result": "CONFIRMED",
                    "new_status": "WORKSPACE_CONVENTION",
                    "verification_method": "static_analysis",
                    "search_scope": scope,
                }
            mono_docs = self._scan_docs_for(r"\bmonolith\b")
            return {
                "actual": f"No core/shared directory marker in inventory; monolith mentioned only in prose ({len(mono_docs)} doc hit(s))",
                "evidence": mono_docs[:3],
                "result": "INCONCLUSIVE",
                "new_status": "UNVERIFIED_PATTERN",
                "verification_method": "static_analysis",
                "search_scope": scope,
                "claim_wording": f"docs claim monolith ({len(mono_docs)} hit(s)); no structural core marker in <complete top-level inventory>",
                "inconclusive_reason": "claim supported by prose only (prose is not behavior); the 'central core' marker is absent or ambiguously named",
            }

        if "microservices" in lowered:
            # Structural signals confirm: service dirs or per-directory deploy
            # manifests (service decomposition footprint). Broker keywords in
            # code are weak (a comment or a detector regex can mention kafka —
            # this very file does), so alone they never confirm.
            structural_hits = [f"{d.relative_to(self.workspace).as_posix()}/" for d in dirs if d.name.lower() in service_names]
            for d in sorted(dirs):
                if any((d / m).exists() for m in ("package.json", "pyproject.toml", "go.mod", "Cargo.toml", "Dockerfile")):
                    if len(structural_hits) < 5:
                        structural_hits.append(f"{d.relative_to(self.workspace).as_posix()}/(manifest)")
            broker_hits: List[str] = []
            for f, text in self._iter_text_files():
                if f.suffix == ".md":
                    continue
                if re.search(r"\b(kafka|rabbitmq|amqp|pubsub|celery|sqs|sns|nats)\b|import grpc|from grpc", text, re.IGNORECASE):
                    broker_hits.append(str(f.relative_to(self.workspace).as_posix()))
                if len(broker_hits) >= 5:
                    break
            if structural_hits:
                return {
                    "actual": f"Microservice decomposition signals found ({len(structural_hits)} item(s): service dirs / deploy manifests)",
                    "evidence": (structural_hits + broker_hits)[:5],
                    "result": "CONFIRMED",
                    "new_status": "WORKSPACE_CONVENTION",
                    "verification_method": "static_analysis",
                    "search_scope": scope,
                }
            if broker_hits:
                return {
                    "actual": f"Broker/messaging keywords appear in code ({len(broker_hits)} file(s)) but no decomposition structure in inventory: {inv}",
                    "evidence": broker_hits[:5],
                    "result": "INCONCLUSIVE",
                    "new_status": "UNVERIFIED_PATTERN",
                    "verification_method": "static_analysis",
                    "search_scope": scope,
                    "claim_wording": "messaging keyword mentions in code (weak signal); no service decomposition in <complete top-level inventory>",
                    "inconclusive_reason": "keyword mentions are not decomposition evidence (a comment or detector regex can contain them); prose/keyword presence is not behavior",
                }
            mono_docs = self._scan_docs_for(r"\bmonolith\b")
            if mono_docs:
                return {
                    "actual": f"Docs explicitly describe a monolith ({mono_docs[0]}); complete inventory shows no service decomposition: {inv}",
                    "evidence": mono_docs[:3],
                    "result": "FALSIFIED",
                    "new_status": "CALIBRATION_ERROR",
                    "verification_method": "static_analysis",
                    "search_scope": scope,
                    "corrected_belief": "Workspace is a single deployable documented as a monolith, not microservices with async communication",
                }
            return {
                "actual": f"Complete inventory shows no service decomposition: {inv}",
                "evidence": [f"{d.relative_to(self.workspace).as_posix()}/" for d in dirs[:5]],
                "result": "FALSIFIED",
                "new_status": "CALIBRATION_ERROR",
                "verification_method": "static_analysis",
                "search_scope": scope,
                "claim_wording": "no service decomposition in <complete top-level inventory>",
                "corrected_belief": f"Workspace is a single application root ({inv}); microservices with async communication requires service decomposition that is absent",
            }

        # Generic architectural pattern: distinctive-word scan in structure (for
        # confirmation) and docs (prose alone is never enough — Phase 0.5).
        words = [w for w in re.findall(r"[a-z][a-z0-9_\-]{3,}", lowered)
                 if w not in {"with", "workspace", "follows", "architecture", "pattern", "strict", "communication", "async"}][:4]
        struct_hits = [f"{w}/" for w in words if w in dir_names]
        doc_hits: List[str] = []
        for w in words:
            doc_hits += [h for h in self._scan_docs_for(re.escape(w)) if h not in doc_hits]
            if len(doc_hits) >= 5:
                break
        if struct_hits:
            return {
                "actual": f"Architectural pattern markers present in structure: {', '.join(struct_hits)}",
                "evidence": struct_hits[:5],
                "result": "CONFIRMED",
                "new_status": "WORKSPACE_CONVENTION",
                "verification_method": "static_analysis",
                "search_scope": scope,
            }
        return {
            "actual": f"No structural marker for '{assumption['statement']}' in scope; doc mentions: {len(doc_hits)}",
            "evidence": doc_hits[:3],
            "result": "INCONCLUSIVE",
            "new_status": "UNVERIFIED_PATTERN",
            "verification_method": "static_analysis",
            "search_scope": scope,
            "inconclusive_reason": "claim supported by prose only (prose is not behavior); no structural marker either way",
        }

    def _test_domain_assumption(self, assumption: Dict) -> Dict:
        """Domain claims are cross-referenced against real doc lines."""
        m = re.match(r"Domain follows (.+) conventions", assumption["statement"])
        domain = m.group(1) if m else assumption["statement"]
        scope = self._search_scope({".md"}, paths=[".", "docs/"])
        hits = self._scan_docs_for(re.escape(domain))
        if hits:
            return {
                "actual": f"Domain '{domain}' referenced in {len(hits)} doc location(s)",
                "evidence": hits,
                "result": "CONFIRMED",
                "new_status": "WORKSPACE_CONVENTION",
                "verification_method": "doc_test_crossref",
                "search_scope": scope,
            }
        return {
            "actual": f"No reference to domain '{domain}' in scoped docs",
            "evidence": [],
            "result": "INCONCLUSIVE",
            "new_status": "DOMAIN_GAP",
            "verification_method": "doc_test_crossref",
            "search_scope": scope,
            "inconclusive_reason": "scoped doc search found no domain evidence; absence is not falsification",
        }

    def _test_user_context_assumption(self, assumption: Dict) -> Dict:
        """User-context assumptions are re-observed against workspace reality.

        Prose confirming prose is a confirm-only probe (Phase 0.5: prose is not
        behavior) — a doc claim needs corroboration outside docs to confirm.
        """
        claim = assumption["statement"]
        kind = assumption.get("user_context_kind", "USER_INTENT")
        confirm_status = "USER_INTENT_VALIDATED" if kind in ("USER_INTENT", "USER_NEED") else "USER_GOAL_VALIDATED"
        falsify_status = {
            "USER_INTENT": "USER_MISALIGNMENT",
            "USER_GOAL": "USER_GOAL_TASK_MISMATCH",
            "USER_NEED": "USER_UNSTATED_REQUIREMENT",
            "USER_TACIT": "USER_TACIT_GAP",
        }.get(kind, "USER_MISALIGNMENT")
        scope = self._search_scope({"*"}, paths=["."])

        # Tacit-debt claim: "Workspace carries N TODO/FIXME markers across M files"
        m = re.search(r"carries (\d+) TODO/FIXME markers across (\d+) files", claim)
        if m:
            todo_count, todo_file_count = 0, set()
            for ext in ("*.py", "*.ts", "*.js", "*.go", "*.rs", "*.java"):
                for f in self.workspace.rglob(ext):
                    if any(part in self._SCAN_SKIP_DIRS for part in f.relative_to(self.workspace).parts):
                        continue
                    try:
                        text = f.read_text(encoding="utf-8", errors="ignore")
                    except OSError:
                        continue
                    hits = len(re.findall(r"TODO|FIXME", text))
                    if hits:
                        todo_count += hits
                        todo_file_count.add(f)
            recorded = (int(m.group(1)), int(m.group(2)))
            actual_counts = (todo_count, len(todo_file_count))
            if actual_counts == recorded:
                return {
                    "actual": f"Recount matches: {todo_count} TODO/FIXME markers across {len(todo_file_count)} files",
                    "evidence": [f"{f.relative_to(self.workspace).as_posix()}" for f in sorted(todo_file_count)[:5]],
                    "result": "CONFIRMED",
                    "new_status": confirm_status,
                    "verification_method": "static_analysis",
                    "search_scope": scope,
                    "user_context": True,
                }
            return {
                "actual": f"Recount finds {todo_count} markers across {len(todo_file_count)} files (recorded {recorded[0]}/{recorded[1]})",
                "evidence": [f"{f.relative_to(self.workspace).as_posix()}" for f in sorted(todo_file_count)[:5]],
                "result": "FALSIFIED",
                "new_status": falsify_status,
                "verification_method": "static_analysis",
                "search_scope": scope,
                "corrected_belief": f"TODO/FIXME debt is {todo_count} markers across {len(todo_file_count)} files, not {recorded[0]}/{recorded[1]}",
                "user_context": True,
            }

        # Goal-vs-reality claim: "...has no test directory"
        if "no test directory" in claim:
            test_dirs = [d for d in ("tests", "test", "__tests__", "spec") if (self.workspace / d).exists()]
            if not test_dirs:
                return {
                    "actual": "Complete top-level inventory reconfirms: no tests/test/__tests__/spec directory",
                    "evidence": [],
                    "result": "CONFIRMED",
                    "new_status": confirm_status,
                    "verification_method": "static_analysis",
                    "search_scope": scope,
                    "claim_wording": "no test directory in <workspace top level>",
                    "user_context": True,
                }
            return {
                "actual": f"Test directory now present: {', '.join(test_dirs)}",
                "evidence": [f"{d}/" for d in test_dirs],
                "result": "FALSIFIED",
                "new_status": falsify_status,
                "verification_method": "static_analysis",
                "search_scope": scope,
                "corrected_belief": f"stated goals are backed by a test directory ({', '.join(test_dirs)}); the no-test-directory claim is stale",
                "user_context": True,
            }

        # Doc claim: corroboration must come from outside docs — prose confirming
        # prose is not verification (§4 confirm-only probes).
        keywords = [w for w in re.findall(r"[A-Za-z][A-Za-z0-9_\-]{3,}", claim.lower())
                    if w not in {"that", "this", "with", "from", "the", "all", "user", "assumption"}][:4]
        code_hits: List[str] = []
        for f, text in self._iter_text_files():
            if f.suffix == ".md":
                continue
            if any(kw in text.lower() for kw in keywords):
                code_hits.append(str(f.relative_to(self.workspace).as_posix()))
                if len(code_hits) >= 5:
                    break
        if code_hits:
            return {
                "actual": f"Claim corroborated outside docs by {len(code_hits)} code/config file(s)",
                "evidence": code_hits,
                "result": "CONFIRMED",
                "new_status": confirm_status,
                "verification_method": "doc_test_crossref",
                "search_scope": scope,
                "user_context": True,
            }
        return {
            "actual": "Claim has no corroboration outside docs within scope",
            "evidence": [],
            "result": "INCONCLUSIVE",
            "new_status": "USER_BLIND_SPOT",
            "verification_method": "doc_test_crossref",
            "search_scope": scope,
            "inconclusive_reason": "claim is prose-only; no behavioral evidence in scope (prose is not behavior)",
            "user_context": True,
        }

    def _compute_calibration_curve(self, calibration_log: List[Dict]) -> Dict:
        """Calibration curve: mean outcome accuracy per stated-confidence band.

        Only measured outcomes count (CONFIRMED = 1.0, FALSIFIED = 0.0);
        INCONCLUSIVE / SKIPPED / KNOWN_FALSE carry no measurement.
        """
        bands = {
            "0.9-1.0": (0.9, 1.01, 0.95),
            "0.7-0.89": (0.7, 0.9, 0.8),
            "0.5-0.69": (0.5, 0.7, 0.6),
            "<0.5": (0.0, 0.5, 0.3),
        }
        result = {}
        for band, (lo, hi, stated_mid) in bands.items():
            outcomes = []
            for r in calibration_log:
                if r["result"] not in ("CONFIRMED", "FALSIFIED"):
                    continue
                stated = float(r.get("stated_confidence", 0.8))
                if lo <= stated < hi:
                    outcomes.append(1.0 if r["result"] == "CONFIRMED" else 0.0)
            if outcomes:
                acc = sum(outcomes) / len(outcomes)
                result[band] = {"stated": stated_mid, "actual": round(acc, 3),
                                "delta": round(acc - stated_mid, 3), "count": len(outcomes)}
            else:
                result[band] = {"stated": stated_mid, "actual": 0, "delta": 0, "count": 0}
        return result

    def _format_workspace_model(self, model: Dict) -> str:
        """Format workspace model as markdown."""
        md = f"# WORKSPACE_MODEL -- {self.workspace.name}\n\n"
        md += f"## Domain\n{model['domain']}\n\n"
        md += "## Stack\n"
        for key, val in model["stack"].items():
            if val:
                md += f"- {key}: {', '.join(val)}\n"
        md += "\n## Structure\n"
        for key, val in model["structure"].items():
            if val:
                md += f"- {key}: {', '.join(val[:10])}\n"
        md += "\n## Detected Conventions (UNVERIFIED_PATTERN)\n"
        for i, conv in enumerate(model["conventions"], 1):
            md += f"{i}. {conv['pattern']} (frequency: {conv['frequency']})\n"
        md += "\n## Memory Index\n"
        for mem in model["memory_index"]:
            md += f"- {mem['name']}: {mem['description']}\n"
        return md

    def _format_blind_spots(self, blind_spots: List[Dict]) -> str:
        """Format blind spots as markdown."""
        md = f"# BLIND SPOT REGISTER -- {self.workspace.name} -- {datetime.now().strftime('%Y-%m-%d')}\n\n"
        md += "## Top Blind Spots by Risk\n\n"
        md += "| Rank | ID | Category | Layer | Severity | Delta | Learning Unit |\n"
        md += "|------|-----|----------|-------|----------|-------|---------------|\n"
        for i, bs in enumerate(blind_spots, 1):
            delta = f"{bs['confidence_delta']:.2f}" if bs['confidence_delta'] else "N/A"
            md += f"| {i} | {bs['id']} | {bs['category']} | {bs['layer']} | {bs['severity']} | {delta} | {bs['learning_unit_id']} |\n"

        md += "\n## Details\n\n"
        for bs in blind_spots:
            md += f"### {bs['id']} -- {bs['severity']} {bs['layer']} {bs['category']}\n"
            md += f"- **Assumption**: {bs['assumption_statement']}\n"
            md += f"- **Evidence**: {bs['evidence_summary']}\n"
            md += f"- **Impact**: {bs['impact']}\n"
            md += f"- **Learning Objective**: {bs['learning_objective']}\n"
            md += f"- **Verification Protocol**: {bs['verification_protocol']}\n"
            md += f"- **Integration Points**: {', '.join(bs['integration_points'])}\n\n"
        return md

    def _format_learning_unit(self, bs: Dict) -> str:
        """Format learning unit as markdown."""
        return f"""# {bs['learning_unit_id']}

## Learning Objective
{bs['learning_objective']}

## Current Belief (Falsified)
{bs['assumption_statement']} -- CALIBRATION_ERROR, delta {bs['confidence_delta']:.2f}

## Corrected Understanding
{bs.get('corrected_belief') or 'To be determined via verification protocol.'}

## Verification Protocol
{bs['verification_protocol']}

## Success Criteria
- Verification protocol executed
- Evidence documented
- Pattern named and described

## Knowledge Artifact
- **Type**: Pattern Doc
- **Location**: `.claude/knowledge/learning-units/{bs['learning_unit_id'].lower()}.md`
- **Memory Pointer**: `.claude/projects/{self._project_slug()}/memory/{bs['learning_unit_id'].lower()}.md`
- **Integration**: {', '.join(bs['integration_points'])}
{self._lu_domain_layer_sections(bs)}

## Status: VERIFIED
"""

    def _lu_domain_layer_sections(self, bs: Dict) -> str:
        """Domain layer (v1.3): optional LU sections for pattern-linked
        blind spots and prior-finding links. Empty string when not
        applicable — additive sections only, the '## Status:' line the
        lifecycle parser matches is untouched."""
        sections = ""
        related = bs.get("related_findings") or []
        if related:
            sections += "\n## Related Prior Findings\n"
            for fid in related[:10]:
                sections += f"- {fid}\n"
        reverify = bs.get("reverify_triggers")
        if reverify:
            sections += "\n## Re-verification Triggers\n"
            if isinstance(reverify, list):
                for t in reverify[:10]:
                    sections += f"- {t}\n"
            else:
                sections += f"- {reverify}\n"
        return sections

    def _format_memory_file(self, lu: Dict) -> str:
        """Format memory file."""
        # Domain layer (v1.3): optional metadata keys only when present in
        # the LU source; required frontmatter is unchanged.
        extra_meta = ""
        related = lu.get("related_findings")
        if related:
            extra_meta += f"  related_findings: {json.dumps(related)}\n"
        reverify = lu.get("reverify_on")
        if reverify:
            extra_meta += f"  reverify_on: {json.dumps(str(reverify))}\n"
        return f"""---
name: {lu['id'].lower()}
description: "{lu['content'].split(chr(10))[2] if len(lu['content'].split(chr(10))) > 2 else 'Learning unit'}"
metadata:
  node_type: memory
  type: project
  originSessionId: self-audit-{datetime.now().strftime('%Y-%m-%d')}
  modified: {datetime.now().isoformat()}
  layer: {lu['layer']}
  verified: true
  calibration_delta: 0.0
{extra_meta}---

{lu['content']}
"""

    def _format_summary(self, assumptions: List, calibration_log: List, blind_spots: List, learning_units: List = None) -> Dict:
        """Format machine-readable summary."""
        summary = {
            "skill": "self-audit",
            "mode": getattr(self, "mode", os.getenv("SELF_AUDIT_MODE", "deep")),
            "target": self.target,
            "stakes": self.stakes,
            "workspace": str(self.workspace),
            "session_id": self.session_id,
            "timestamp": datetime.now().isoformat(),
            "assumptions_tested": len(calibration_log),
            "confirmed": sum(1 for r in calibration_log if r["result"] == "CONFIRMED"),
            "falsified": sum(1 for r in calibration_log if r["result"] == "FALSIFIED"),
            "inconclusive": sum(1 for r in calibration_log if r["result"] == "INCONCLUSIVE"),
            "blind_spots": len(blind_spots),
            "learning_units": len(learning_units) if learning_units else 0,
            "top_blind_spots": [bs["id"] for bs in blind_spots[:5]],
            "recommended_preload": ["workspace-model"] + [f"{lu['id'].lower()}" for lu in (learning_units or [])[:3]]
        }
        # Domain-adaptive layer (v1.3): additive keys only — existing
        # consumers (dashboard, graders) read specific keys and are unaffected.
        stats = getattr(self, "_domain_layer_stats", None)
        summary["domain_layer"] = bool(stats)
        if stats:
            summary["schema_version"] = domain_analysis.SCHEMA_VERSION
            summary["finding_count"] = stats["finding_count"]
            summary["pattern_candidate_count"] = stats["pattern_candidate_count"]
            summary["blind_spot_candidate_count"] = stats["blind_spot_candidate_count"]
        return summary

    def _write_json(self, path: Path, data: Any):
        path.write_text(json.dumps(data, indent=2))

    def _write_markdown(self, path: Path, content: str):
        path.parent.mkdir(parents=True, exist_ok=True)
        path.write_text(content)

    def _append_jsonl(self, path: Path, records: List[Dict]):
        path.parent.mkdir(parents=True, exist_ok=True)
        with path.open("a") as f:
            for record in records:
                f.write(json.dumps(record) + "\n")


def main():
    parser = argparse.ArgumentParser(description="Self-Audit: Epistemic calibration for any workspace")
    parser.add_argument("--mode", choices=["quick", "standard", "deep"], default=None,
                        help="Depth mode (default: derived from --stakes, else SELF_AUDIT_MODE, else deep)")
    parser.add_argument("--workspace", default=None)
    parser.add_argument("--target", choices=["workspace", "plan", "diff", "last-answer"], default=None,
                        help="What is being audited (SKILL.md §7; default: workspace)")
    parser.add_argument("--stakes", choices=["low", "medium", "high"], default=None,
                        help="Verification budget (SKILL.md §7; default: medium; sets the default mode)")
    parser.add_argument("--output-dir", default=None)
    parser.add_argument("--no-cross-model", action="store_true")
    parser.add_argument("--no-trend", action="store_true")
    parser.add_argument("--user-context", action="store_true",
                        help="Also discover and calibrate user-context assumptions (intent, needs, tacit knowledge, goal-task fit)")
    parser.add_argument("--verbose", action="store_true")
    parser.add_argument("--audit-purpose", default=None,
                        help="Stated outcome for task resolution (default: not stated — "
                             "honestly labeled as inferred from the workspace scan)")
    args = parser.parse_args()

    # Apply CLI args to environment BEFORE initializing CLI
    if args.workspace:
        os.environ["SELF_AUDIT_WORKSPACE"] = args.workspace
    if args.target:
        os.environ["SELF_AUDIT_TARGET"] = args.target
    if args.stakes:
        os.environ["SELF_AUDIT_STAKES"] = args.stakes
    if args.output_dir:
        os.environ["SELF_AUDIT_KNOWLEDGE_ROOT"] = args.output_dir
    if args.no_cross_model:
        os.environ["SELF_AUDIT_CROSS_MODEL"] = "false"
    if args.no_trend:
        os.environ["SELF_AUDIT_TREND_ANALYSIS"] = "false"
    if args.user_context:
        os.environ["SELF_AUDIT_USER_CONTEXT"] = "true"
    if args.verbose:
        os.environ["SELF_AUDIT_VERBOSE"] = "true"
    if args.audit_purpose:
        os.environ["SELF_AUDIT_AUDIT_PURPOSE"] = args.audit_purpose

    # Mode resolution (SKILL.md §7): explicit --mode wins; else explicit --stakes
    # picks the default mode (low->quick, medium->standard, high->deep);
    # else SELF_AUDIT_MODE env; else deep (backward-compatible default).
    if args.mode is None:
        if args.stakes:
            args.mode = {"low": "quick", "medium": "standard", "high": "deep"}[args.stakes]
        else:
            args.mode = os.getenv("SELF_AUDIT_MODE", "deep")

    cli = SelfAuditCLI()
    sys.exit(cli.run(args))


if __name__ == "__main__":
    main()