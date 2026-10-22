# Self-Audit Skill — Troubleshooting Guide

## Common Issues and Solutions

### 1. Skill Not Loading / Not Triggering

**Symptoms:**
- `/self-audit` not recognized
- Skill not in `/skills` list
- Auto-invocation not working

**Solutions:**

```bash
# 1. Check skill is installed
/skills

# 2. Verify frontmatter parses (must be first line!)
head -5 .claude/skills/self-audit/SKILL.md
# Should start with: ---

# 3. Check for refused name
claude --debug 2>&1 | grep -i "self-audit"
# Look for: [names] refusal

# 4. Reload skills
/reload-skills

# 5. Check plugin installed
claude plugin list

# 6. Reinstall if needed
claude plugin install self-audit@marketplace --scope project --trust-plugin
```

**Common Causes:**
- Frontmatter `---` not on line 1
- Invalid YAML in frontmatter (silent failure)
- Directory name doesn't match frontmatter `name`
- Reserved name conflict (`synced`, `anthropic-skills`)
- Invalid characters in name (see naming constraints)

---

### 2. Permission Denied Writing to `.claude/`

**Symptoms:**
- "Permission denied" errors
- Artifacts not created
- Calibration log not written

**Solutions:**

```bash
# 1. Grant write permission in Claude Code settings
# Settings → Permissions → Add .claude/ directory

# 2. Or use custom output directory
/self-audit --mode quick --output-dir /tmp/self-audit-output

# 3. Or set environment variable
export SELF_AUDIT_KNOWLEDGE_ROOT=/custom/path
/self-audit --mode quick

# 4. Check directory ownership
ls -la .claude/
# Fix if needed: chown -R $USER .claude/
```

---

### 3. Workspace Not Found

**Symptoms:**
- "Workspace not found" error
- Wrong directory audited

**Solutions:**

```bash
# 1. Explicit workspace path
/self-audit --mode quick --workspace /absolute/path/to/project

# 2. Environment variable
export SELF_AUDIT_WORKSPACE=/absolute/path/to/project
/self-audit --mode quick

# 3. Check CLAUDE_PROJECT_DIR
echo $CLAUDE_PROJECT_DIR
# Should be set by Claude Code automatically

# 4. Verify workspace exists
ls -la /path/to/project
```

---

### 4. No Calibration History / Empty Trend Analysis

**Symptoms:**
- "No prior calibration history" message
- Trend report shows only 1 session
- Cross-model validation finds no history

**Solutions:**

```bash
# This is NORMAL for first run!
# Calibration log builds over multiple sessions.

# Check log exists
cat .claude/knowledge/calibration.log.jsonl

# Run multiple sessions to build history
/self-audit --mode quick  # Session 1
/self-audit --mode quick  # Session 2 (different workspace or after changes)
/self-audit --mode quick  # Session 3 → trend analysis now works

# Trend analysis requires ≥3 sessions by default
export SELF_AUDIT_TREND_MIN_SESSIONS=2  # Lower threshold
/self-audit --mode deep
```

---

### 5. Cross-Model Validation Fails

**Symptoms:**
- "Cross-model validation failed" error
- Reviewer agents not spawning
- Validation log empty

**Solutions:**

```bash
# 1. Disable if not needed
export SELF_AUDIT_CROSS_MODEL=false
/self-audit --mode deep

# 2. Or use standard mode (no cross-model)
/self-audit --mode standard

# 3. Check API quota / rate limits
# Cross-model spawns 2 subagents → uses API calls

# 4. Reduce reviewers
export SELF_AUDIT_CROSS_MODEL_REVIEWERS=1
/self-audit --mode deep

# 5. Check subagent permissions
# Subagents inherit parent session permissions
```

---

### 6. Calibration Log Corrupted / Invalid JSONL

**Symptoms:**
- "Invalid JSONL" errors
- Analytics script fails
- Malformed lines in log

**Solutions:**

```bash
# 1. Backup and inspect
cp .claude/knowledge/calibration.log.jsonl .claude/knowledge/calibration.log.jsonl.bak
cat .claude/knowledge/calibration.log.jsonl

# 2. Find bad lines
python -c "
import json
with open('.claude/knowledge/calibration.log.jsonl') as f:
    for i, line in enumerate(f, 1):
        try:
            json.loads(line)
        except json.JSONDecodeError as e:
            print(f'Line {i}: {e}')
            print(f'  {line[:100]}')
"

# 3. Fix or remove bad lines
# Or start fresh (archive old)
mv .claude/knowledge/calibration.log.jsonl .claude/knowledge/calibration.log.jsonl.old
# Skill will create new log
```

---

### 7. Memory System Not Working

**Symptoms:**
- Memory files not created
- MEMORY.md not updated
- Learning units not persisted

**Solutions:**

```bash
# 1. Check memory directory exists
ls -la .claude/projects/*/memory/

# 2. Create if missing
mkdir -p .claude/projects/$(basename $PWD | tr '[:upper:]' '[:lower:]' | tr ' ' '-')/memory

# 3. Check permissions
ls -la .claude/projects/

# 4. Custom memory root
export SELF_AUDIT_MEMORY_ROOT=/custom/memory/path
/self-audit --mode standard

# 5. Symlink approach (recommended)
ln -s /custom/memory/path .claude/projects/my-project/memory
```

---

### 8. Assumptions Not Being Tested

**Symptoms:**
- Calibration log has fewer entries than assumptions
- "Inconclusive" for everything
- No falsified records

**Solutions:**

```bash
# 1. Check testable flag in assumptions.json
cat .claude/knowledge/assumptions.json | jq '.[] | select(.testable==true)'

# 2. Run with verbose to see what's happening
export SELF_AUDIT_VERBOSE=true
/self-audit --mode standard

# 3. Check workspace has files to test against
ls -la /workspace/

# 4. Use standalone validator for debugging
python .claude/skills/self-audit/scripts/validate-assumptions.py \
  --assumptions .claude/knowledge/assumptions.json \
  --workspace . \
  --output /tmp/test-log.jsonl
```

---

### 9. Blind Spots Not Detected / Wrong Ranking

**Symptoms:**
- No blind spots found
- Wrong severity/layer classification
- Top 5 doesn't match expectations

**Solutions:**

```bash
# 1. Check calibration log has falsified records
grep FALSIFIED .claude/knowledge/calibration.log.jsonl

# 2. Verify threshold
export SELF_AUDIT_BLIND_SPOT_THRESHOLD=0.3  # Lower threshold
/self-audit --mode quick

# 3. Check layer classification in assumptions
cat .claude/knowledge/assumptions.json | jq '.[] | .layer'

# 4. Manual inspection of blind spot generation
# Risk = severity_weight × layer_weight
# L4=4, L3=3, L2=2, L1=1
# Critical=4, High=3, Medium=2, Low=1
```

---

### 10. Learning Units Not Created

**Symptoms:**
- No `.claude/knowledge/learning-units/` files
- Memory files not written
- Status stays PENDING

**Solutions:**

```bash
# 1. Only CRITICAL/HIGH blind spots create learning units
# Check blind-spots.md for severity
grep -A2 "Critical\|High" .claude/knowledge/blind-spots.md

# 2. Check learning units directory
ls -la .claude/knowledge/learning-units/

# 3. Verify Phase 4-5 executed
# Quick mode only does memory, not full learning units
/self-audit --mode standard  # Creates learning units
/self-audit --mode deep     # Creates learning units

# 4. Check memory root writable
touch .claude/projects/*/memory/test.md && rm .claude/projects/*/memory/test.md
```

---

### 11. Scripts Not Executing / Import Errors

**Symptoms:**
- `run-self-audit.py` import errors
- `ModuleNotFoundError`
- Scripts not found in PATH

**Solutions:**

```bash
# 1. Run from skill directory
cd .claude/skills/self-audit/
python scripts/run-self-audit.py --mode quick

# 2. Use CLAUDE_SKILL_DIR (set by skill)
# Skill sets this automatically when invoked via /self-audit

# 3. Install dependencies
pip install -r requirements.txt  # if exists

# 4. Check Python version (3.10+ required)
python --version
```

---

### 12. Eval Failures

**Symptoms:**
- `claude plugin eval` fails
- Graders not passing
- Threshold not met

**Solutions:**

```bash
# 1. Run specific case
claude plugin eval . --case case-quick-mode --trust-plugin --threshold 0.8

# 2. Check grader logic
# Graders are in evals/case-*/graders/*.md

# 3. Debug with verbose
claude plugin eval . --case case-quick-mode --trust-plugin --json results.json
cat results.json | jq '.cases[].graders[]'

# 4. Common grader issues:
# - Artifacts not in expected location
# - JSON/JSONL format invalid
# - Markdown parsing differences
```

---

### 13. Plugin Validation Errors

**Symptoms:**
- `claude plugin validate` fails
- Frontmatter validation errors
- Manifest errors

**Solutions:**

```bash
# 1. Validate with details
claude plugin validate . --strict --json

# 2. Check plugin.json schema
cat .claude-plugin/plugin.json | jq '.'

# 3. Check marketplace.json
cat .claude-plugin/marketplace.json | jq '.'

# 4. Validate skill directory
claude plugin validate ./skills/self-audit --strict --json

# 5. Common issues:
# - Missing required fields (name in plugin.json)
# - Invalid paths in skills array
# - Version mismatch
# - Homepage URL not parseable
```

---

### 14. Installation Issues

**Symptoms:**
- `claude plugin install` fails
- Marketplace not found
- Version conflicts

**Solutions:**

```bash
# 1. Add marketplace first
claude plugin marketplace add rrxprotex/self-audit-skill --scope project
claude plugin install self-audit@self-audit-marketplace

# 2. One-liner (v2.1.292+)
claude plugin install self-audit@rrxprotex/self-audit-skill --marketplace rrxprotex/self-audit-skill

# 3. Check plugin installed
claude plugin list

# 4. Update to latest
claude plugin update self-audit

# 5. Remove and reinstall
claude plugin remove self-audit
claude plugin install self-audit@marketplace
```

---

### 15. Performance / Timeout Issues

**Symptoms:**
- Skill times out
- Phases take too long
- Subagent spawns hang

**Solutions:**

```bash
# 1. Use quick mode for faster results
/self-audit --mode quick

# 2. Reduce assumption count
export SELF_AUDIT_MAX_ASSUMPTIONS=30
export SELF_AUDIT_QUICK_TOP_N=10
/self-audit --mode standard

# 3. Disable cross-model and trend
export SELF_AUDIT_CROSS_MODEL=false
export SELF_AUDIT_TREND_ANALYSIS=false
/self-audit --mode deep

# 4. Limit workspace scope
# Audit specific subdirectory
/self-audit --mode quick --workspace /project/src/module
```

---

## Debug Mode

Enable verbose logging for any issue:

```bash
# Environment variable
export SELF_AUDIT_VERBOSE=true
/self-audit --mode quick

# Or with skill
/self-audit --mode quick  # Check invocation logs in Claude Code

# Debug plugin loading
claude --debug 2>&1 | grep -i "self-audit\|skill\|plugin"
```

---

## Log Locations

| Log | Location |
|-----|----------|
| Calibration log | `.claude/knowledge/calibration.log.jsonl` |
| Cross-model validation | `.claude/knowledge/cross-model-validation.log.jsonl` |
| Trend report | `.claude/knowledge/calibration-trend-report.md` |
| Skill invocation | Claude Code debug log (`claude --debug`) |
| Plugin install | `~/.claude/plugins/` or project `.claude/plugins/` |

---

## Getting Help

1. **Check this guide** for common issues
2. **Search existing issues** on GitHub
3. **Open a new issue** with:
   - Error message (full)
   - Steps to reproduce
   - Environment: `claude --version`, `python --version`, OS
   - Relevant log excerpts
4. **Start a discussion** for design questions

---

## Quick Diagnostic Checklist

Run this to diagnose most issues:

```bash
#!/bin/bash
# self-audit-diagnose.sh

echo "=== Self-Audit Diagnostics ==="
echo

echo "1. Claude Code version:"
claude --version

echo
echo "2. Plugin installed:"
claude plugin list | grep self-audit || echo "  NOT INSTALLED"

echo
echo "3. Skill loaded:"
/skills 2>&1 | grep -i self-audit || echo "  NOT LOADED"

echo
echo "4. Frontmatter valid:"
head -1 .claude/skills/self-audit/SKILL.md 2>/dev/null || echo "  SKILL.md not found"

echo
echo "5. Plugin manifest:"
cat .claude-plugin/plugin.json 2>/dev/null | jq '.name, .version' || echo "  plugin.json not found"

echo
echo "6. Workspace accessible:"
echo "  CLAUDE_PROJECT_DIR: ${CLAUDE_PROJECT_DIR:-NOT SET}"
echo "  PWD: $(pwd)"

echo
echo "7. .claude/ writable:"
touch .claude/test_write 2>/dev/null && rm .claude/test_write && echo "  YES" || echo "  NO"

echo
echo "8. Calibration log:"
if [ -f .claude/knowledge/calibration.log.jsonl ]; then
    echo "  Exists: $(wc -l < .claude/knowledge/calibration.log.jsonl) lines"
else
    echo "  NOT FOUND"
fi

echo
echo "9. Memory directory:"
ls -la .claude/projects/*/memory/ 2>/dev/null || echo "  NOT FOUND"

echo
echo "=== Diagnostics Complete ==="
```