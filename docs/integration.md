# Self-Audit Skill — Integration Guide

## Overview

Self-Audit integrates with the Claude Code skill ecosystem to provide continuous epistemic calibration. This guide covers integration patterns with other skills and custom adapters.

## Skill Integration Matrix

| Skill | Integration Type | Direction | Description |
|-------|------------------|-----------|-------------|
| `using-agent-skills` | Pre-check hook | Self-Audit → using-agent-skills | Run quick mode before major tasks |
| `doubt-driven-development` | Doubt seeds | Self-Audit → doubt-driven-development | Feed L3/L4 blind spots as adversarial targets |
| `context-engineering` | Context provider | Self-Audit → context-engineering | Load WORKSPACE_MODEL + top learning units |
| `universal-brainstorming` | Seed provider | Self-Audit → universal-brainstorming | Use blind spots as PROBE seeds |
| `spec-driven-development` | Assumption validator | Self-Audit → spec-driven-development | Cross-reference spec assumptions |
| `code-review-and-quality` | Calibration checker | Self-Audit → code-review-and-quality | Flag overconfident comments |
| `planning-and-task-breakdown` | Risk input | Self-Audit → planning | Weight task risk by blind spot severity |

---

## 1. Using-Agent-Skills Pre-Check Hook

### Automatic Integration

Add to your `using-agent-skills` skill or create a hook:

```markdown
## Pre-Task Calibration (Auto)

Before any major implementation task:

1. **Run quick self-audit:**
   ```
   /self-audit --mode quick
   ```

2. **Load calibration summary:**
   ```bash
   # Read last session summary
   cat .claude/knowledge/calibration-summary.json
   ```

3. **Load top 3 learning units:**
   ```bash
   # From calibration-summary.json recommended_preload
   for lu in $(jq -r '.recommended_preload[]' .claude/knowledge/calibration-summary.json); do
     if [ -f ".claude/knowledge/learning-units/$lu.md" ]; then
       cat ".claude/knowledge/learning-units/$lu.md"
     fi
   done
   ```

4. **Feed to context-engineering:**
   ```
   Context files = [WORKSPACE_MODEL.md, LU-1, LU-2, LU-3, CALIBRATION_SUMMARY.json]
   ```

### Hook Implementation (Claude Code Hooks)

```json
// .claude/hooks/pre-task-calibration.json
{
  "hooks": [
    {
      "event": "TaskStart",
      "matcher": "major|implementation|refactor|architecture",
      "command": "/self-audit --mode quick",
      "description": "Run quick self-audit before major tasks"
    }
  ]
}
```

### Benefits

- Every major task starts with calibrated knowledge
- Reduces repeated calibration errors
- Loads relevant blind spots automatically
- Tracks calibration improvement per task

---

## 2. Doubt-Driven-Development Integration

### Feeding Blind Spots as Doubt Seeds

```bash
# 1. Run self-audit (any mode)
/self-audit --mode standard

# 2. Extract L3/L4 blind spots
python -c "
import json, re
with open('.claude/knowledge/blind-spots.md') as f:
    content = f.read()

# Parse table rows
import re
rows = re.findall(r'\|\s*(\d+)\s*\|\s*(BS-\d+)\s*\|\s*(\w+)\s*\|\s*(L\d)\s*\|\s*(\w+)\s*', content)
l3_l4 = [r for r in rows if r[3] in ('L3', 'L4') and r[4] in ('Critical', 'High')]

for r in l3_l4:
    print(f'{r[1]}: {r[2]} {r[3]} {r[4]}')
" > /tmp/doubt-seeds.txt

# 3. Invoke doubt-driven-development with seeds
/doubt-driven-development --seeds /tmp/doubt-seeds.txt --target "authentication refactor"
```

### Automated Hook

```json
// .claude/hooks/blind-spots-to-doubts.json
{
  "hooks": [
    {
      "event": "PostToolUse",
      "matcher": "Skill:self-audit",
      "command": "python .claude/scripts/blind_spots_to_doubts.py",
      "description": "Convert blind spots to doubt seeds"
    }
  ]
}
```

### `blind_spots_to_doubts.py` Script

```python
#!/usr/bin/env python3
"""Convert self-audit blind spots to doubt-driven-development seeds."""
import json, re
from pathlib import Path

blind_spots_path = Path(".claude/knowledge/blind-spots.md")
content = blind_spots_path.read_text()

# Parse blind spots table
rows = re.findall(r'\|\s*(\d+)\s*\|\s*(BS-\d+)\s*\|\s*(\w+)\s*\|\s*(L\d)\s*\|\s*(\w+)', content)

seeds = []
for rank, bs_id, category, layer, severity in rows:
    if layer in ('L3', 'L4') and severity in ('Critical', 'High'):
        # Extract detail section
        detail_match = re.search(f'### {bs_id}.*?(?=### |\Z)', content, re.DOTALL)
        if detail_match:
            detail = detail_match.group(0)
            assumption = re.search(r'\*\*Assumption\*\*:\s*(.+)', detail)
            impact = re.search(r'\*\*Impact\*\*:\s*(.+)', detail)
            seeds.append({
                "id": bs_id,
                "category": category,
                "layer": layer,
                "severity": severity,
                "assumption": assumption.group(1) if assumption else "",
                "impact": impact.group(1) if impact else "",
                "doubt": f"Is it true that {assumption.group(1) if assumption else 'this assumption'}?"
            })

# Write seeds file
seeds_path = Path(".claude/knowledge/doubt-seeds.json")
seeds_path.write_text(json.dumps(seeds, indent=2))
print(f"Generated {len(seeds)} doubt seeds at {seeds_path}")
```

---

## 3. Context-Engineering Integration

### Primary Context Files

Self-Audit produces the ideal context loading set for `context-engineering`:

```bash
# Priority context files (in order)
CONTEXT_FILES=(
  ".claude/knowledge/workspace-model.md"          # 1. Workspace snapshot
  ".claude/knowledge/calibration-summary.json"    # 2. Calibration awareness
)

# Add top verified learning units (L2+)
for lu in $(jq -r '.recommended_preload[]' .claude/knowledge/calibration-summary.json 2>/dev/null | grep -v "workspace-model"); do
  if [ -f ".claude/knowledge/learning-units/$lu.md" ]; then
    CONTEXT_FILES+=(".claude/knowledge/learning-units/$lu.md")
  fi
done

# Load into context-engineering
/context-engineering --load "${CONTEXT_FILES[@]}"
```

### Context-Engineering Skill Configuration

```yaml
# In context-engineering skill or config
context_sources:
  - name: self-audit-workspace-model
    path: ".claude/knowledge/workspace-model.md"
    priority: 1
    always_load: true
  
  - name: self-audit-calibration-summary
    path: ".claude/knowledge/calibration-summary.json"
    priority: 2
    always_load: true
  
  - name: self-audit-learning-units
    pattern: ".claude/knowledge/learning-units/*.md"
    priority: 3
    filter:
      status: "VERIFIED"
      min_layer: "L2"
    max_count: 5
```

---

## 4. Universal-Brainstorming Integration

### Blind Spots as PROBE Seeds

```bash
# 1. Run self-audit
/self-audit --mode standard

# 2. Extract blind spots for brainstorming
python -c "
import json
with open('.claude/knowledge/blind-spots.md') as f:
    content = f.read()

# Convert to brainstorming seeds
import re
seeds = re.findall(r'### (BS-\d+).*?\*\*Assumption\*\*:\s*(.+)\n.*?\*\*Learning Objective\*\*:\s*(.+)', content, re.DOTALL)

for bs_id, assumption, objective in seeds:
    print(f'Seed: {bs_id}')
    print(f'  Assumption: {assumption}')
    print(f'  Explore: {objective}')
    print()
" > /tmp/brainstorm-seeds.txt

# 3. Feed to universal-brainstorming
/universal-brainstorming --seeds /tmp/brainstorm-seeds.txt --topic "architecture patterns"
```

### Brainstorming Phase Integration

In `universal-brainstorming` PROBE phase, use:
- `ASSUMPTION_REGISTER.json` → assumption hunt input
- `BLIND_SPOT_REGISTER.md` → blind spot seeds
- `CALIBRATION_LOG.jsonl` → calibration error patterns

---

## 5. Spec-Driven-Development Integration

### Assumption Validation Against Specs

```bash
# 1. Run self-audit to get calibration log
/self-audit --mode standard

# 2. Extract spec assumptions (from SPEC.md, ADRs, etc.)
# 3. Cross-reference with calibration log
python -c "
import json

# Load calibration log
cal_log = []
with open('.claude/knowledge/calibration.log.jsonl') as f:
    for line in f:
        if line.strip():
            cal_log.append(json.loads(line))

# Build falsified assumptions map
falsified = {r['assumption_id']: r for r in cal_log if r['result'] == 'FALSIFIED'}

# Check spec assumptions (pseudo-code)
# spec_assumptions = parse_spec('SPEC.md')
# for sa in spec_assumptions:
#     if sa.id in falsified:
#         print(f'SPEC ASSUMPTION CONFLICT: {sa.id} - {falsified[sa.id][\"actual\"]}')

print(f'Falsified assumptions to check against specs: {list(falsified.keys())}')
"
```

### Spec Assumption Annotation

Add to your specs:
```markdown
## Assumptions

| ID | Assumption | Self-Audit Status | Calibration Delta |
|----|------------|-------------------|-------------------|
| SPEC-001 | All services use Result<T,E> | CALIBRATION_ERROR | -0.75 |
| SPEC-002 | Async messaging only | CALIBRATION_ERROR | -0.90 |
| SPEC-003 | Config via YAML | WORKSPACE_CONVENTION | +0.10 |
```

---

## 6. Code-Review-and-Quality Integration

### Calibration Check in Reviews

```bash
# Hook: Check for calibration errors in reviewed code
# .claude/hooks/calibration-check.json
{
  "hooks": [
    {
      "event": "PreToolUse",
      "matcher": "Edit|Write",
      "command": "python .claude/scripts/calibration_check.py",
      "description": "Check for overconfident comments and unverified assumptions"
    }
  ]
}
```

### `calibration_check.py` Script

```python
#!/usr/bin/env python3
"""Check code changes for calibration issues."""
import sys, re
from pathlib import Path

# Patterns indicating overconfidence/unverified assumptions
PATTERNS = [
    (r'# (?:assume|assuming|obviously|clearly|of course)', 'Overconfident comment'),
    (r'# (?:probably|maybe|should work|likely)', 'Unverified assumption'),
    (r'TODO: (?:verify|check|confirm)', 'Unverified TODO'),
    (r'FIXME: (?:assumption|calibration)', 'Known calibration issue'),
]

def check_file(filepath):
    try:
        content = Path(filepath).read_text()
        issues = []
        for pattern, desc in PATTERNS:
            for match in re.finditer(pattern, content, re.IGNORECASE):
                line_num = content[:match.start()].count('\n') + 1
                issues.append(f"{filepath}:{line_num}: {desc} - {match.group()}")
        return issues
    except:
        return []

if __name__ == "__main__":
    # Get files from args or stdin
    files = sys.argv[1:] if len(sys.argv) > 1 else sys.stdin.read().split()
    
    all_issues = []
    for f in files:
        all_issues.extend(check_file(f))
    
    if all_issues:
        print("⚠️  Calibration issues found:")
        for issue in all_issues:
            print(f"  {issue}")
        # Don't block, just warn
    else:
        print("✅ No calibration issues detected")
```

---

## 7. Planning-and-Task-Breakdown Integration

### Risk Weighting by Blind Spots

```bash
# 1. Get blind spots with severity
python -c "
import json, re
with open('.claude/knowledge/blind-spots.md') as f:
    content = f.read()

rows = re.findall(r'\|\s*(\d+)\s*\|\s*(BS-\d+)\s*\|\s*(\w+)\s*\|\s*(L\d)\s*\|\s*(\w+)', content)

risk_weights = {'Critical': 4, 'High': 3, 'Medium': 2, 'Low': 1}
layer_weights = {'L4': 4, 'L3': 3, 'L2': 2, 'L1': 1}

for rank, bs_id, category, layer, severity in rows:
    risk = risk_weights[severity] * layer_weights[layer]
    print(f'{bs_id}: risk={risk} ({severity} {layer} {category})')
" > /tmp/task-risks.txt

# 2. Feed to planning
/planning-and-task-breakdown --risk-input /tmp/task-risks.txt --target "refactor auth module"
```

---

## 8. Memory System Adapters

### Default Memory Adapter (Project-Scoped)

```python
# Built-in: writes to .claude/projects/<slug>/memory/
# slug = sanitized workspace name
```

### Custom Memory Adapter

Implement `MemoryAdapter` interface for non-standard memory systems:

```python
# my_memory_adapter.py
class MemoryAdapter:
    def __init__(self, config):
        self.config = config
    
    def write_memory(self, slug: str, content: str, metadata: dict) -> bool:
        """Write memory file. Return True on success."""
        # Your implementation
        pass
    
    def read_memory(self, slug: str) -> str:
        """Read memory file. Return content or empty string."""
        pass
    
    def list_memories(self) -> list:
        """List all memory slugs."""
        pass
    
    def update_index(self, entries: list) -> bool:
        """Update MEMORY.md index."""
        pass
```

### Register Custom Adapter

```bash
# Environment variable
export SELF_AUDIT_MEMORY_ADAPTER=my_memory_adapter.MemoryAdapter

# Or in .self-audit.yaml (future)
memory:
  adapter: "my_memory_adapter.MemoryAdapter"
  config:
    backend: "sqlite"
    path: "/custom/memory.db"
```

### Example: SQLite Memory Adapter

```python
# sqlite_memory_adapter.py
import sqlite3, json
from pathlib import Path
from typing import Dict, List

class SQLiteMemoryAdapter:
    def __init__(self, config: Dict):
        self.db_path = Path(config.get("path", ".claude/memory.db"))
        self.db_path.parent.mkdir(parents=True, exist_ok=True)
        self._init_db()
    
    def _init_db(self):
        with sqlite3.connect(self.db_path) as conn:
            conn.execute("""
                CREATE TABLE IF NOT EXISTS memories (
                    slug TEXT PRIMARY KEY,
                    content TEXT NOT NULL,
                    metadata TEXT NOT NULL,
                    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                    updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
                )
            """)
            conn.execute("""
                CREATE TABLE IF NOT EXISTS memory_index (
                    slug TEXT PRIMARY KEY,
                    description TEXT,
                    layer TEXT,
                    verified BOOLEAN,
                    calibration_delta REAL
                )
            """)
    
    def write_memory(self, slug: str, content: str, metadata: Dict) -> bool:
        with sqlite3.connect(self.db_path) as conn:
            conn.execute(
                "INSERT OR REPLACE INTO memories (slug, content, metadata) VALUES (?, ?, ?)",
                (slug, content, json.dumps(metadata))
            )
            conn.execute(
                "INSERT OR REPLACE INTO memory_index (slug, description, layer, verified, calibration_delta) VALUES (?, ?, ?, ?, ?)",
                (slug, metadata.get("description", ""), metadata.get("layer", ""), metadata.get("verified", False), metadata.get("calibration_delta", 0.0))
            )
        return True
    
    def read_memory(self, slug: str) -> str:
        with sqlite3.connect(self.db_path) as conn:
            row = conn.execute("SELECT content FROM memories WHERE slug = ?", (slug,)).fetchone()
            return row[0] if row else ""
    
    def list_memories(self) -> List[str]:
        with sqlite3.connect(self.db_path) as conn:
            return [row[0] for row in conn.execute("SELECT slug FROM memories")]
    
    def update_index(self, entries: List[Dict]) -> bool:
        # Entries: [{"slug": "...", "description": "..."}, ...]
        with sqlite3.connect(self.db_path) as conn:
            for e in entries:
                conn.execute(
                    "INSERT OR REPLACE INTO memory_index (slug, description) VALUES (?, ?)",
                    (e["slug"], e.get("description", ""))
                )
        return True
```

---

## 9. CI/CD Integration

### GitHub Actions Pre-Merge Check

```yaml
# .github/workflows/calibration-check.yml
name: Calibration Check

on:
  pull_request:
    branches: [main]

jobs:
  calibration-check:
    runs-on: ubuntu-latest
    steps:
      - uses: actions/checkout@v4
      
      - name: Install Claude Code
        run: npm install -g @anthropic-ai/claude-code@latest
      
      - name: Install self-audit skill
        run: claude plugin install self-audit@marketplace --scope project
      
      - name: Run quick calibration
        run: /self-audit --mode quick
      
      - name: Check for critical blind spots
        run: |
          python -c "
          import re
          with open('.claude/knowledge/blind-spots.md') as f:
              content = f.read()
          
          # Check for Critical L3/L4
          rows = re.findall(r'\|\s*\d+\s*\|\s*(BS-\d+)\s*\|\s*(\w+)\s*\|\s*(L\d)\s*\|\s*(\w+)', content)
          critical_l3_l4 = [r for r in rows if r[2] in ('L3', 'L4') and r[3] == 'Critical']
          
          if critical_l3_l4:
              print('::error::Critical L3/L4 blind spots found:')
              for r in critical_l3_l4:
                  print(f'  {r[0]}: {r[1]} {r[2]} {r[3]}')
              exit(1)
          else:
              print('✅ No critical L3/L4 blind spots')
          "
```

### Scheduled Calibration (Nightly)

```yaml
# .github/workflows/nightly-calibration.yml
name: Nightly Calibration

on:
  schedule:
    - cron: '0 2 * * *'  # 2 AM UTC daily

jobs:
  nightly-calibration:
    runs-on: ubuntu-latest
    steps:
      - uses: actions/checkout@v4
      
      - name: Install Claude Code
        run: npm install -g @anthropic-ai/claude-code@latest
      
      - name: Install self-audit
        run: claude plugin install self-audit@marketplace --scope project
      
      - name: Run deep calibration
        run: |
          /self-audit --mode deep
      
      - name: Upload calibration artifacts
        uses: actions/upload-artifact@v4
        with:
          name: calibration-artifacts
          path: .claude/knowledge/
          retention-days: 30
      
      - name: Check calibration trend
        run: |
          python .claude/skills/self-audit/scripts/calibration-analytics.py \
            --log .claude/knowledge/calibration.log.jsonl \
            --output calibration-trend-report.md
      
      - name: Comment on calibration trend
        if: github.repository_owner == 'rrxprotex'
        uses: actions/github-script@v7
        with:
          script: |
            const fs = require('fs');
            const report = fs.readFileSync('calibration-trend-report.md', 'utf8');
            // Post to issue or discussion
```

---

## 10. Custom Workspace Integration

### Multi-Workspace Calibration

```bash
# Calibrate multiple workspaces
for ws in /projects/*/; do
  echo "=== Calibrating $ws ==="
  /self-audit --mode quick --workspace "$ws" --output-dir "/audit-results/$(basename $ws)"
done

# Aggregate results
python -c "
import json, glob
all_summaries = []
for f in glob.glob('/audit-results/*/calibration-summary.json'):
    with open(f) as fp:
        all_summaries.append(json.load(fp))

# Cross-workspace analysis
print(f'Calibrated {len(all_summaries)} workspaces')
for s in all_summaries:
    print(f'  {s[\"workspace\"]}: {s[\"falsified\"]} falsified, {s[\"blind_spots\"]} blind spots')
"
```

### Monorepo Sub-Project Calibration

```bash
# For monorepos with multiple sub-projects
/self-audit --mode standard --workspace /monorepo/packages/auth
/self-audit --mode standard --workspace /monorepo/packages/api
/self-audit --mode standard --workspace /monorepo/packages/shared
```

---

## Summary: Integration Checklist

- [ ] **using-agent-skills**: Add pre-check hook for quick mode
- [ ] **doubt-driven-development**: Feed L3/L4 blind spots as doubt seeds
- [ ] **context-engineering**: Load WORKSPACE_MODEL + top learning units
- [ ] **universal-brainstorming**: Use blind spots as PROBE seeds
- [ ] **spec-driven-development**: Cross-reference spec assumptions
- [ ] **code-review-and-quality**: Add calibration check hook
- [ ] **planning-and-task-breakdown**: Weight risks by blind spot severity
- [ ] **Memory adapter**: Implement custom if not using default
- [ ] **CI/CD**: Add calibration check to PR pipeline
- [ ] **Scheduled**: Nightly deep calibration for trend tracking

---

## Troubleshooting Integration Issues

| Issue | Solution |
|-------|----------|
| Skill not triggering | Check `/skills`, verify frontmatter, run `/reload-skills` |
| Memory not persisting | Verify `.claude/projects/<slug>/memory/` writable |
| Context not loading | Check `context-engineering` config, file paths |
| Doubt seeds not working | Verify `doubt-driven-development` installed |
| Domain layer unwanted | `export SELF_AUDIT_DOMAIN_LAYER=false` — disables the v1.3 layer entirely |
| Cross-model shows NOT_RUN | Configure `SELF_AUDIT_EXTERNAL_REVIEWERS` or accept the honest not-run state |
| CI calibration fails | Check permissions, API keys, workspace path |