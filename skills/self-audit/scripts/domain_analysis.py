#!/usr/bin/env python3
"""
Domain-Adaptive Analysis Engine — schema, validators, and candidate nomination
for the Self-Audit domain layer (v1.3).

Design split (plan principle): the skill agent (LLM) does semantics — domain
modeling, concept-distinction criteria, causal/alternative explanations,
layer selection. This module does evidence discipline only: schema
validation, scope recording, duplicate-content detection (copies are not
independent evidence), status gating, and depth control.

Honesty bound: every heuristic signal this module emits is labeled CANDIDATE
(a nomination, never a finding). Promotion beyond CANDIDATE happens only in
the agent workflow with cited evidence; verification-grade pattern statuses
additionally require the independence gate below.

Usage:
  python domain_analysis.py --report <path>   # validate a report file (exit 1 on errors)
  python domain_analysis.py --example         # print a filled example report
"""
import argparse
import hashlib
import json
import re
import sys
from typing import Dict, List, Optional, Tuple

SCHEMA_VERSION = "1"

# --- finding schema ---
REQUIRED_FINDING_FIELDS = [
    "id", "statement", "category_path", "layer", "evidence_status",
    "source_refs", "confidence_band",
]
FINDING_ID_PATTERN = r"^FIND-\d{3,}$"
PATTERN_ID_PATTERN = r"^PAT-\d{3,}$"
BLIND_SPOT_CANDIDATE_ID_PATTERN = r"^BSX-\d{3,}$"
EVIDENCE_STATUS_VALUES = ["OBSERVED", "CANDIDATE", "INFERRED", "HYPOTHESIS", "UNVERIFIED_CLAIM"]
CONFIDENCE_BANDS = ["HIGH", "MEDIUM", "LOW"]
LAYERS = ["L1", "L2", "L3", "L4"]
CONCEPT_STATUS_VALUES = ["ESTABLISHED", "PROPOSED"]
PATTERN_STATUS_VALUES = ["VERIFIED", "PROBABLE", "CANDIDATE"]
COMPLEXITY_VALUES = ["SIMPLE", "MULTISTEP", "UNCERTAIN"]
CATEGORY_PATH_MAX_DEPTH = 4  # dot-separated, e.g. "root.sub.concept"
_CATEGORY_SEGMENT_RE = re.compile(r"^[A-Za-z0-9_-]{2,60}$")

TASK_RESOLUTION_FIELDS = [
    "stated_outcome", "inferred_purpose", "object_of_analysis",
    "resource_scope", "access_limits", "complexity", "cost_of_error",
    "verification_criteria", "open_clarifications",
]


# ---------------------------------------------------------------------------
# Content fingerprinting (duplicate sources are not independent evidence)
# ---------------------------------------------------------------------------

def content_key(text: str) -> str:
    """Normalized content fingerprint: lowercase, collapse whitespace, strip
    punctuation, sha256 hex[:16]."""
    normalized = re.sub(r"[^\w\s]", "", (text or "").lower())
    normalized = re.sub(r"\s+", " ", normalized).strip()
    return hashlib.sha256(normalized.encode("utf-8")).hexdigest()[:16]


def _token_set(text: str) -> set:
    normalized = re.sub(r"[^\w\s]", "", (text or "").lower())
    return {t for t in normalized.split() if len(t) > 2}


def distinct_source_count(source_refs: list, ref_contents: Optional[Dict[str, str]] = None) -> int:
    """Count independent sources. If ref_contents is provided, two refs with
    identical content_key are ONE source (copies are not independent
    evidence). Without ref_contents, falls back to unique ref strings; the
    caller should record that the count is provisional via
    independence.note."""
    if not isinstance(source_refs, list):
        return 0
    refs = [str(r) for r in source_refs if r]
    if ref_contents is not None:
        keys = set()
        for r in refs:
            if r in ref_contents:
                keys.add(content_key(ref_contents[r]))
            else:
                # ref without known content counts as its own (unique) source
                keys.add("ref:" + r)
        return len(keys)
    return len(set(refs))


# ---------------------------------------------------------------------------
# Validators
# ---------------------------------------------------------------------------

def validate_finding(finding: dict) -> List[str]:
    """Return list of error strings (empty = valid)."""
    errors: List[str] = []
    if not isinstance(finding, dict):
        return ["finding is not an object"]
    fid = finding.get("id", "")
    errors += [f"finding id missing/invalid ({fid!r}, expected FIND-NNN)"
               for _ in [1] if not re.match(FINDING_ID_PATTERN, str(fid))]
    for field in REQUIRED_FINDING_FIELDS:
        if field not in finding:
            errors.append(f"finding {fid}: missing required field '{field}'")
    if errors and not fid:
        return errors
    if not str(finding.get("statement", "")).strip():
        errors.append(f"finding {fid}: 'statement' is empty")
    path = str(finding.get("category_path", ""))
    segments = path.split(".") if path else []
    if not segments or len(segments) > CATEGORY_PATH_MAX_DEPTH or \
            any(not _CATEGORY_SEGMENT_RE.match(s) for s in segments):
        errors.append(
            f"finding {fid}: 'category_path' must be 1..{CATEGORY_PATH_MAX_DEPTH} "
            f"dot-separated segments of [A-Za-z0-9_-]{{2,60}} (got {path!r})")
    if finding.get("layer") not in LAYERS:
        errors.append(f"finding {fid}: 'layer' must be one of {LAYERS}")
    if finding.get("evidence_status") not in EVIDENCE_STATUS_VALUES:
        errors.append(f"finding {fid}: 'evidence_status' must be one of {EVIDENCE_STATUS_VALUES}")
    if not isinstance(finding.get("source_refs"), list):
        errors.append(f"finding {fid}: 'source_refs' must be a list (may be empty)")
    elif not finding["source_refs"] and not str(finding.get("evidence_scope", "")).strip():
        errors.append(
            f"finding {fid}: empty source_refs requires 'evidence_scope' stating "
            f"where was searched (a null search confirms nothing beyond its scope)")
    if finding.get("confidence_band") not in CONFIDENCE_BANDS:
        errors.append(f"finding {fid}: 'confidence_band' must be one of {CONFIDENCE_BANDS}")
    if finding.get("evidence_status") not in ("OBSERVED",) and \
            not str(finding.get("uncertainty_reason", "")).strip():
        errors.append(f"finding {fid}: non-OBSERVED findings require 'uncertainty_reason'")
    supersedes = finding.get("supersedes")
    if supersedes is not None and not re.match(FINDING_ID_PATTERN, str(supersedes)):
        errors.append(f"finding {fid}: 'supersedes' must be a FIND-NNN id")
    return errors


def validate_domain_model(model: dict) -> Tuple[List[str], List[str]]:
    """Validate a domain model. Returns (errors, warnings).

    model = {"subject": str, "concepts": [{"name": str, "definition": str,
    "distinguishes": [{"criterion": str, "vs_concept": str}],
    "status": "ESTABLISHED|PROPOSED"}], "coverage_notes": str or list}
    """
    errors: List[str] = []
    warnings: List[str] = []
    if not isinstance(model, dict):
        return ["domain_model is not an object"], warnings
    if not str(model.get("subject", "")).strip():
        errors.append("domain_model: 'subject' is required and non-empty")
    concepts = model.get("concepts")
    if not isinstance(concepts, list):
        errors.append("domain_model: 'concepts' must be a list")
        concepts = []
    seen_names: Dict[str, str] = {}
    for i, concept in enumerate(concepts):
        if not isinstance(concept, dict):
            errors.append(f"domain_model.concepts[{i}]: not an object")
            continue
        name = str(concept.get("name", "")).strip()
        if not name:
            errors.append(f"domain_model.concepts[{i}]: 'name' is required")
        elif name in seen_names:
            if seen_names[name] != str(concept.get("definition", "")):
                warnings.append(
                    f"domain_model: concept name collision '{name}' with different "
                    f"definitions — same path, different meanings; split or unify explicitly")
        else:
            seen_names[name] = str(concept.get("definition", ""))
        if not str(concept.get("definition", "")).strip():
            errors.append(f"domain_model.concepts[{i}] ({name}): 'definition' is required")
        if concept.get("status") not in CONCEPT_STATUS_VALUES:
            errors.append(
                f"domain_model.concepts[{i}] ({name}): 'status' must be one of "
                f"{CONCEPT_STATUS_VALUES} (a newly constructed category is PROPOSED, "
                f"never presented as established knowledge)")
        distinguishes = concept.get("distinguishes", [])
        if not isinstance(distinguishes, list):
            errors.append(f"domain_model.concepts[{i}] ({name}): 'distinguishes' must be a list")
            distinguishes = []
        for j, d in enumerate(distinguishes):
            if not isinstance(d, dict) or not str(d.get("criterion", "")).strip() \
                    or not str(d.get("vs_concept", "")).strip():
                errors.append(
                    f"domain_model.concepts[{i}] ({name}).distinguishes[{j}]: "
                    f"requires non-empty 'criterion' and 'vs_concept'")
    return errors, warnings


def validate_pattern(p: dict, finding_ids: Optional[set] = None) -> List[str]:
    """Validate one pattern record. Status gating for VERIFIED/PROBABLE needs
    the full findings context and happens in validate_analysis_report; this
    function checks shape only, plus member-ref resolvability when
    finding_ids is given."""
    errors: List[str] = []
    if not isinstance(p, dict):
        return ["pattern is not an object"]
    pid = str(p.get("id", ""))
    if not re.match(PATTERN_ID_PATTERN, pid):
        errors.append(f"pattern id missing/invalid ({pid!r}, expected PAT-NNN)")
    if not str(p.get("statement", "")).strip():
        errors.append(f"pattern {pid}: 'statement' is required")
    members = p.get("member_finding_ids")
    if not isinstance(members, list) or not members:
        errors.append(f"pattern {pid}: 'member_finding_ids' must be a non-empty list")
    elif finding_ids is not None:
        for m in members:
            if m not in finding_ids:
                errors.append(f"pattern {pid}: member_finding_ids references unknown finding {m!r}")
    if not isinstance(p.get("source_refs"), list):
        errors.append(f"pattern {pid}: 'source_refs' must be a list")
    independence = p.get("independence")
    if not isinstance(independence, dict) or not isinstance(
            independence.get("distinct_sources", None), int):
        errors.append(
            f"pattern {pid}: 'independence.distinct_sources' (integer) is required "
            f"(copies of the same content are one source, not independent evidence)")
    if p.get("status") not in PATTERN_STATUS_VALUES:
        errors.append(f"pattern {pid}: 'status' must be one of {PATTERN_STATUS_VALUES}")
    return errors


def validate_task_resolution(tr: dict) -> List[str]:
    """Validate the task-resolution block."""
    errors: List[str] = []
    if not isinstance(tr, dict):
        return ["task_resolution is not an object"]
    if not str(tr.get("stated_outcome", "")).strip():
        errors.append("task_resolution: 'stated_outcome' is required and non-empty")
    if tr.get("complexity") not in COMPLEXITY_VALUES:
        errors.append(f"task_resolution: 'complexity' must be one of {COMPLEXITY_VALUES}")
    inferred = tr.get("inferred_purpose")
    if inferred is not None:
        if not isinstance(inferred, dict) or \
                str(inferred.get("labeled_as", "")) != "INFERENCE":
            errors.append(
                "task_resolution: 'inferred_purpose' must carry "
                "'labeled_as': 'INFERENCE' (inferences are never presented as user intent)")
        elif not str(inferred.get("purpose", inferred.get("text", ""))).strip():
            errors.append("task_resolution: 'inferred_purpose' needs the purpose text")
    oc = tr.get("open_clarifications")
    if oc is not None and not isinstance(oc, list):
        errors.append("task_resolution: 'open_clarifications' must be a list")
    return errors


def validate_blind_spot_candidate(bs: dict) -> List[str]:
    errors: List[str] = []
    if not isinstance(bs, dict):
        return ["blind_spot_candidate is not an object"]
    bid = str(bs.get("id", ""))
    if not re.match(BLIND_SPOT_CANDIDATE_ID_PATTERN, bid):
        errors.append(f"blind_spot_candidate id missing/invalid ({bid!r}, expected BSX-NNN)")
    for field in ("description", "why_it_matters", "smallest_useful_check"):
        if not str(bs.get(field, "")).strip():
            errors.append(
                f"blind_spot_candidate {bid}: '{field}' is required — a named gap "
                f"must say why it matters and which check would settle it")
    return errors


def validate_analysis_report(report: dict) -> List[str]:
    errors: List[str] = []
    if not isinstance(report, dict):
        return ["report is not an object"]
    if str(report.get("schema_version", "")) != SCHEMA_VERSION:
        errors.append(f"report: 'schema_version' must be '{SCHEMA_VERSION}'")
    if not str(report.get("subject", "")).strip():
        errors.append("report: 'subject' is required and non-empty")

    findings = report.get("findings", [])
    if not isinstance(findings, list):
        errors.append("report: 'findings' must be a list")
        findings = []
    finding_ids = set()
    for f in findings:
        errs = validate_finding(f)
        errors += [f"report.findings: {e}" for e in errs]
        if isinstance(f, dict) and re.match(FINDING_ID_PATTERN, str(f.get("id", ""))):
            finding_ids.add(f["id"])

    patterns = report.get("patterns", [])
    if not isinstance(patterns, list):
        errors.append("report: 'patterns' must be a list")
        patterns = []
    for p in patterns:
        errs = validate_pattern(p, finding_ids)
        errors += [f"report.patterns: {e}" for e in errs]
        if not isinstance(p, dict):
            continue
        status = p.get("status")
        distinct = p.get("independence", {}).get("distinct_sources", 0) \
            if isinstance(p.get("independence"), dict) else 0
        if status == "VERIFIED":
            # Honesty gate: VERIFIED means the stated verification actually
            # RAN this session. Two sources + resolvable members are
            # necessary but not sufficient — a check that never ran cannot
            # back a VERIFIED claim.
            verification_status = str(p.get("verification_status", "NOT_RUN"))
            verification_evidence = p.get("verification_evidence")
            evidence_ok = isinstance(verification_evidence, list) and \
                len(verification_evidence) > 0 and \
                all(str(e).strip() for e in verification_evidence)
            if distinct < 2 or errs:
                errors.append(
                    f"report.patterns: {p.get('id')}: status VERIFIED requires >= 2 "
                    f"distinct sources and resolvable members (got {distinct}); "
                    f"downgrade to CANDIDATE or PROBABLE until the gate passes")
            elif verification_status != "RUN" or not evidence_ok:
                errors.append(
                    f"report.patterns: {p.get('id')}: status VERIFIED requires "
                    f"verification_status='RUN' and non-empty 'verification_evidence' "
                    f"citing the check that actually ran (commands/tool output); "
                    f"a check never run cannot back VERIFIED — downgrade to "
                    f"CANDIDATE or PROBABLE")
        elif status == "PROBABLE" and distinct < 1:
            errors.append(
                f"report.patterns: {p.get('id')}: status PROBABLE requires >= 1 "
                f"distinct source; downgrade to CANDIDATE")

    bs_candidates = report.get("blind_spot_candidates", [])
    if not isinstance(bs_candidates, list):
        errors.append("report: 'blind_spot_candidates' must be a list")
        bs_candidates = []
    for bs in bs_candidates:
        errs = validate_blind_spot_candidate(bs)
        errors += [f"report.blind_spot_candidates: {e}" for e in errs]

    domain_model = report.get("domain_model")
    if domain_model is not None:
        dm_errors, _warnings = validate_domain_model(domain_model)
        errors += [f"report.domain_model: {e}" for e in dm_errors]

    task_resolution = report.get("task_resolution")
    if task_resolution is not None:
        errors += [f"report.task_resolution: {e}" for e in validate_task_resolution(task_resolution)]

    scope = report.get("scope")
    if scope is not None and not isinstance(scope, dict):
        errors.append("report: 'scope' must be an object")
    return errors


# ---------------------------------------------------------------------------
# Pattern candidate nomination (deterministic, lexical only — CANDIDATE only)
# ---------------------------------------------------------------------------

def nominate_pattern_candidates(findings: list, similarity_threshold: float = 0.6) -> List[dict]:
    """Group findings whose statements share >= threshold token-Jaccard.

    Output candidates carry status='CANDIDATE' plus 'lexical_signal' and
    'member_finding_ids'. NEVER promotes beyond CANDIDATE — a lexical
    signal can nominate, it cannot establish meaning or a pattern.
    Deterministic ordering (sorted ids)."""
    valid = [f for f in findings if isinstance(f, dict) and f.get("statement")]
    tokens = {id(f): _token_set(f["statement"]) for f in valid}

    def jaccard(a: set, b: set) -> float:
        if not a or not b:
            return 0.0
        return len(a & b) / len(a | b)

    # Union-find grouping over the similarity threshold
    parent = {i: i for i in range(len(valid))}

    def find(i: int) -> int:
        while parent[i] != i:
            parent[i] = parent[parent[i]]
            i = parent[i]
        return i

    best_similarity = 0.0
    for i in range(len(valid)):
        for j in range(i + 1, len(valid)):
            sim = jaccard(tokens[id(valid[i])], tokens[id(valid[j])])
            best_similarity = max(best_similarity, sim)
            if sim >= similarity_threshold:
                ri, rj = find(i), find(j)
                if ri != rj:
                    parent[ri] = rj

    groups: Dict[int, List[dict]] = {}
    for i, f in enumerate(valid):
        groups.setdefault(find(i), []).append(f)

    candidates = []
    for members in groups.values():
        if len(members) < 2:
            continue  # a single occurrence is never a recurring-pattern conclusion
        member_ids = sorted(str(m.get("id", "")) for m in members)
        source_refs = sorted({str(r) for m in members
                              for r in (m.get("source_refs") or []) if r})
        statement = members[0]["statement"]
        candidates.append({
            "id": "PAT-%03d" % (len(candidates) + 1),
            "statement": f"Recurring across {len(members)} findings: {statement}",
            "member_finding_ids": member_ids,
            "source_refs": source_refs,
            "status": "CANDIDATE",  # lexical nomination only — never promoted here
            "lexical_signal": {"jaccard": round(best_similarity, 3)},
            "independence": {
                "distinct_sources": distinct_source_count(source_refs),
                "note": "lexical nomination; distinct_sources counted from unique refs "
                        "(content dedupe applied only when ref contents are provided)",
            },
        })
    candidates.sort(key=lambda c: c["id"])
    return candidates


# ---------------------------------------------------------------------------
# Depth control (mirrors SKILL.md budget table — quick stays cheap)
# ---------------------------------------------------------------------------

def analysis_depth(mode: str, stakes: str, complexity: str) -> dict:
    """Deterministic depth selection. mode in quick|standard|deep;
    stakes in low|medium|high; complexity in SIMPLE|MULTISTEP|UNCERTAIN.

    The output never injects domain-specific category names — depth control
    is structural, so one domain's categories can never be forced onto
    another."""
    if mode not in ("quick", "standard", "deep"):
        raise ValueError(f"mode must be quick|standard|deep, got {mode!r}")
    if stakes not in ("low", "medium", "high"):
        raise ValueError(f"stakes must be low|medium|high, got {stakes!r}")
    if complexity not in COMPLEXITY_VALUES:
        raise ValueError(f"complexity must be one of {COMPLEXITY_VALUES}, got {complexity!r}")

    base = {
        "quick": {"task_resolution": True, "domain_model": False,
                  "layered_analysis": False, "pattern_discovery": False,
                  "blind_spot_search": True, "max_layers": 3},
        "standard": {"task_resolution": True, "domain_model": True,
                     "layered_analysis": True, "pattern_discovery": True,
                     "blind_spot_search": True, "max_layers": 6},
        "deep": {"task_resolution": True, "domain_model": True,
                 "layered_analysis": True, "pattern_discovery": True,
                 "blind_spot_search": True, "max_layers": 10},
    }[mode]

    # stakes=high upgrades quick->standard depth for domain_model only
    if mode == "quick" and stakes == "high":
        base["domain_model"] = True
    # complexity=SIMPLE never increases depth; UNCERTAIN upgrades
    # standard->deep for pattern_discovery and blind_spot_search
    if mode == "standard" and complexity == "UNCERTAIN":
        base["pattern_discovery"] = True
        base["blind_spot_search"] = True
        base["max_layers"] = 10
    return base


# ---------------------------------------------------------------------------
# Example report (for --example; neutral, domain-independent)
# ---------------------------------------------------------------------------

EXAMPLE_REPORT = {
    "schema_version": SCHEMA_VERSION,
    "subject": "sample-workspace",
    "task_resolution": {
        "stated_outcome": "Decide whether the config-loading convention is consistent before refactoring",
        "inferred_purpose": {
            "purpose": "The user likely wants to know if a refactor is safe",
            "labeled_as": "INFERENCE",
            "basis": "refactor language in docs; not confirmed by the user",
        },
        "object_of_analysis": "workspace",
        "resource_scope": {"workspace": "/path/to/ws", "env_overrides": []},
        "access_limits": [
            "files outside the workspace root are not read",
            "plan/diff/last-answer targets have no CLI-side content ingestion",
        ],
        "complexity": "MULTISTEP",
        "cost_of_error": "a wrong convention belief would misdirect the refactor",
        "verification_criteria": "re-scan of all config files with recorded scope",
        "open_clarifications": [],
    },
    "domain_model": {
        "subject": "config-loading conventions",
        "concepts": [
            {
                "name": "reservation",
                "definition": "a temporary allocation that expires unless confirmed",
                "distinguishes": [
                    {"criterion": "expires without confirmation", "vs_concept": "hold"},
                ],
                "status": "ESTABLISHED",
            },
            {
                "name": "hold",
                "definition": "a blocking state preventing other allocations",
                "distinguishes": [
                    {"criterion": "does not expire; requires explicit release", "vs_concept": "reservation"},
                ],
                "status": "PROPOSED",
            },
        ],
        "coverage_notes": "no concepts derived for error-handling; area unclassified",
    },
    "findings": [
        {
            "id": "FIND-001",
            "statement": "Config files mix YAML (root) and JSON (runtime)",
            "category_path": "config.format.convention",
            "layer": "L2",
            "evidence_status": "OBSERVED",
            "source_refs": ["config.yaml", "runtime/settings.json"],
            "confidence_band": "HIGH",
        },
        {
            "id": "FIND-002",
            "statement": "Config loading follows a shared helper in two modules",
            "category_path": "config.loading.mechanism",
            "layer": "L2",
            "evidence_status": "INFERRED",
            "source_refs": ["src/main.py", "src/utils.py"],
            "confidence_band": "MEDIUM",
            "uncertainty_reason": "inferred from import structure; helper behavior not executed",
        },
    ],
    "patterns": [
        {
            "id": "PAT-001",
            "statement": "Recurring across 2 findings: Config loading follows a shared helper in two modules",
            "member_finding_ids": ["FIND-001", "FIND-002"],
            "source_refs": ["src/main.py", "src/utils.py"],
            "status": "CANDIDATE",
            "lexical_signal": {"jaccard": 0.62},
            "independence": {"distinct_sources": 2, "note": "lexical nomination only"},
        },
    ],
    "blind_spot_candidates": [
        {
            "id": "BSX-001",
            "description": "No test directory exists while docs describe verified behavior",
            "why_it_matters": "the docs' claims about checks are unbacked; affects the refactor decision",
            "smallest_useful_check": "search the workspace for any test runner config",
        },
    ],
    "scope": {
        "inspected": ["src/", "docs/", "config.yaml", "runtime/"],
        "not_inspected": ["generated/"],
        "note": "not-found means not found under the stated scope, never does-not-exist",
    },
}


def main():
    parser = argparse.ArgumentParser(
        description="Domain-Adaptive Analysis Engine: schema validation and "
                    "candidate nomination for the self-audit domain layer")
    parser.add_argument("--report", default=None,
                        help="Path to an analysis-findings.json report to validate "
                             "(exit 1 on validation errors)")
    parser.add_argument("--example", action="store_true",
                        help="Print a filled example report JSON to stdout")
    args = parser.parse_args()

    if args.example:
        print(json.dumps(EXAMPLE_REPORT, indent=2))
        return 0
    if args.report:
        try:
            with open(args.report, encoding="utf-8") as f:
                report = json.load(f)
        except (OSError, json.JSONDecodeError) as e:
            print(f"ERROR: cannot read report {args.report}: {e}", file=sys.stderr)
            return 1
        errors = validate_analysis_report(report)
        if errors:
            print(f"VALIDATION FAILED ({len(errors)} error(s)):", file=sys.stderr)
            for e in errors:
                print(f"  - {e}", file=sys.stderr)
            return 1
        print("VALIDATION OK: report passes the domain-layer schema")
        return 0
    parser.print_help()
    return 0


if __name__ == "__main__":
    sys.exit(main())
