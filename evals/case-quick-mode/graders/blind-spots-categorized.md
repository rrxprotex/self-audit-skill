# Grader: Blind Spots Categorized

## Purpose
Verify that blind-spots.md contains properly categorized and ranked blind spots with all required fields.

## Pass Criteria
1. File exists and is valid markdown with a table of top blind spots
2. Each blind spot has: `id`, `category`, `layer`, `severity`, `confidence_delta`, `learning_unit_id`
3. Categories are valid: `CALIBRATION_ERROR`, `UNVERIFIED_CRITICAL`, `IMPLICIT_CONVENTION_GAP`, `DOMAIN_GAP`, `MEMORY_DRIFT`, `POSSIBLE_BLIND_SPOT`
4. Layers are valid: `L1`, `L2`, `L3`, `L4`
5. Severities are valid: `Critical`, `High`, `Medium`, `Low`
6. Top 5 ranked by risk = severity_weight × layer_weight
7. At least 1 blind spot is `CALIBRATION_ERROR` with L3/L4 layer
8. Each blind spot has `learning_objective`, `verification_protocol`, `integration_points`

## Fail Criteria
- Missing required fields
- Invalid category/layer/severity values
- Ranking not by risk (severity × layer weight)
- No L3/L4 calibration errors when they exist in calibration log
- Learning unit IDs don't follow `LU-NNN` format
- Integration points empty or not referencing known skills

## Evaluation Method
```python
import re

content = open('.claude/knowledge/blind-spots.md').read()

# Parse table
table_match = re.search(r'\| Rank \| ID \| Category \| Layer \| Severity \| Delta \| Learning Unit \|\n\|.*?\n((?:\|.*?\n)*)', content)
assert table_match, "Blind spots table not found"

rows = table_match.group(1).strip().split('\n')
blind_spots = []
for row in rows:
    parts = [p.strip() for p in row.split('|')[1:-1]]
    if len(parts) >= 7:
        blind_spots.append({
            "rank": int(parts[0]),
            "id": parts[1],
            "category": parts[2],
            "layer": parts[3],
            "severity": parts[4],
            "delta": parts[5],
            "learning_unit": parts[6]
        })

assert len(blind_spots) >= 5, f"Expected at least 5 blind spots, got {len(blind_spots)}"

# Validate each
valid_categories = {"CALIBRATION_ERROR", "UNVERIFIED_CRITICAL", "IMPLICIT_CONVENTION_GAP", "DOMAIN_GAP", "MEMORY_DRIFT", "POSSIBLE_BLIND_SPOT"}
valid_layers = {"L1", "L2", "L3", "L4"}
valid_severities = {"Critical", "High", "Medium", "Low"}

severity_weight = {"Critical": 4, "High": 3, "Medium": 2, "Low": 1}
layer_weight = {"L4": 4, "L3": 3, "L2": 2, "L1": 1}

prev_risk = float('inf')
has_l3_l4_cal_error = False

for bs in blind_spots:
    assert bs["category"] in valid_categories, f"Invalid category: {bs['category']}"
    assert bs["layer"] in valid_layers, f"Invalid layer: {bs['layer']}"
    assert bs["severity"] in valid_severities, f"Invalid severity: {bs['severity']}"
    assert re.match(r'LU-\d{3}', bs["learning_unit"]), f"Invalid learning unit ID: {bs['learning_unit']}"
    
    risk = severity_weight[bs["severity"]] * layer_weight[bs["layer"]]
    assert risk <= prev_risk, f"Ranking not by risk: {bs['id']} risk {risk} > prev {prev_risk}"
    prev_risk = risk
    
    if bs["category"] == "CALIBRATION_ERROR" and bs["layer"] in ("L3", "L4"):
        has_l3_l4_cal_error = True

# Check details sections exist for each
for bs in blind_spots:
    detail_header = f"### {bs['id']}"
    assert detail_header in content, f"Detail section missing for {bs['id']}"
    
    # Check required fields in detail
    for field in ["Assumption", "Evidence", "Learning Objective", "Verification Protocol", "Integration Points"]:
        assert f"**{field}**:" in content or f"**{field}**" in content, f"Missing {field} in {bs['id']} detail"

assert has_l3_l4_cal_error, "No L3/L4 CALIBRATION_ERROR blind spots found"

print(f"Valid: {len(blind_spots)} blind spots, ranked by risk, L3/L4 calibration errors present")
```