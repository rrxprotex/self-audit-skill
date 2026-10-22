#!/usr/bin/env python3
"""
Self-Audit Dashboard Generator — turn calibration artifacts into a single
self-contained HTML dashboard (inline SVG charts, no external dependencies).

Reads the knowledge root produced by run-self-audit.py:
  - calibration-summary.json
  - calibration.log.jsonl
  - blind-spots.md  (optional; falls back to the log)

Writes: <knowledge-root>/dashboard.html  (or --output)

Usage:
  python generate-dashboard.py --knowledge-root .claude/knowledge
  SELF_AUDIT_KNOWLEDGE_ROOT=.claude/knowledge python generate-dashboard.py

The same HTML is what gets published as a live Artifact — it bakes a JSON
payload and renders charts in vanilla JS/SVG, so it works offline.
"""
import argparse
import json
import os
import re
from collections import Counter, defaultdict
from datetime import datetime
from pathlib import Path


def load_jsonl(path: Path):
    records = []
    if not path.exists():
        return records
    for line in path.read_text(encoding="utf-8").splitlines():
        line = line.strip()
        if line:
            try:
                records.append(json.loads(line))
            except Exception:
                pass
    return records


def parse_blind_spots(path: Path):
    """Parse the ranked blind-spot table out of blind-spots.md."""
    if not path.exists():
        return []
    text = path.read_text(encoding="utf-8")
    m = re.search(
        r"\| Rank \| ID \| Category \| Layer \| Severity \| Delta \| Learning Unit \|\n\|.*?\n((?:\|.*?\n)*)",
        text,
    )
    if not m:
        return []
    rows = []
    for row in m.group(1).strip().split("\n"):
        parts = [p.strip() for p in row.split("|")[1:-1]]
        if len(parts) >= 7:
            try:
                delta = float(parts[5])
            except ValueError:
                delta = None
            rows.append({
                "rank": int(parts[0]) if parts[0].isdigit() else len(rows) + 1,
                "id": parts[1],
                "category": parts[2],
                "layer": parts[3],
                "severity": parts[4],
                "delta": delta,
                "learning_unit": parts[6],
            })
    return rows


def build_payload(knowledge_root: Path) -> dict:
    summary = {}
    sp = knowledge_root / "calibration-summary.json"
    if sp.exists():
        try:
            summary = json.loads(sp.read_text(encoding="utf-8"))
        except Exception:
            summary = {}

    log = load_jsonl(knowledge_root / "calibration.log.jsonl")
    blind_spots = parse_blind_spots(knowledge_root / "blind-spots.md")

    # --- KPI row ---
    results = Counter(r.get("result") for r in log)
    total = len(log)
    kpis = {
        "tested": total,
        "confirmed": results.get("CONFIRMED", 0),
        "falsified": results.get("FALSIFIED", 0),
        "inconclusive": results.get("INCONCLUSIVE", 0),
        "blind_spots": len(blind_spots) if blind_spots else summary.get("blind_spots", 0),
        "learning_units": summary.get("learning_units", 0),
    }

    # --- Calibration curve: stated-confidence band -> actual accuracy + delta ---
    bands = [
        ("0.9-1.0", 0.9, 1.0),
        ("0.7-0.89", 0.7, 0.9),
        ("0.5-0.69", 0.5, 0.7),
        ("<0.5", 0.0, 0.5),
    ]
    curve = []
    for label, lo, hi in bands:
        in_band = []
        for r in log:
            # stated confidence is not stored per-record; recover a proxy:
            # confidence_delta = actual - stated, and result gives the direction.
            # Use the record's implied stated band via confidence where available.
            stated = r.get("stated_confidence")
            if stated is None:
                continue
            if lo <= stated < hi or (hi == 1.0 and stated == 1.0):
                in_band.append(r)
        if in_band:
            # actual accuracy = share of CONFIRMED in the band
            acc = sum(1 for r in in_band if r.get("result") == "CONFIRMED") / len(in_band)
            mean_stated = sum(r.get("stated_confidence", 0) for r in in_band) / len(in_band)
            curve.append({
                "band": label,
                "count": len(in_band),
                "actual": round(acc, 3),
                "stated": round(mean_stated, 3),
                "delta": round(acc - mean_stated, 3),
            })

    # If per-record stated confidence is unavailable, derive a coarse curve from
    # result + delta so the chart is never empty but stays honest (marked derived).
    if not curve and log:
        derived = True
        for label, lo, hi in bands:
            members = []
            for r in log:
                d = r.get("confidence_delta", 0)
                stated = 1.0 - abs(d)  # proxy: small delta -> high stated confidence
                if lo <= stated < hi or (hi == 1.0 and stated == 1.0):
                    members.append(r)
            if members:
                acc = sum(1 for r in members if r.get("result") == "CONFIRMED") / len(members)
                mean_stated = sum(1.0 - abs(r.get("confidence_delta", 0)) for r in members) / len(members)
                curve.append({
                    "band": label,
                    "count": len(members),
                    "actual": round(acc, 3),
                    "stated": round(mean_stated, 3),
                    "delta": round(acc - mean_stated, 3),
                })
    else:
        derived = False

    # --- Blind spots by category (sequential magnitude) ---
    cat_counts = Counter(b["category"] for b in blind_spots)
    if not cat_counts:
        # fall back to statuses in the log
        cat_counts = Counter(
            r.get("new_status") for r in log
            if r.get("result") == "FALSIFIED"
        )
    categories = [{"name": k, "value": v} for k, v in cat_counts.most_common()]

    # --- Layer breakdown (sequential) ---
    layer_counts = Counter(r.get("layer") for r in log)
    layers = [{"name": k, "value": layer_counts[k]} for k in ["L1", "L2", "L3", "L4"] if layer_counts.get(k)]

    # --- Result mix (part-to-whole) ---
    result_mix = [{"name": k, "value": v} for k, v in results.most_common() if k]

    # --- Trend: session -> mean |delta| ---
    by_session = defaultdict(list)
    for r in log:
        by_session[r.get("session_id", "unknown")].append(abs(r.get("confidence_delta", 0)))
    trend = []
    for sid in sorted(by_session.keys()):
        vals = by_session[sid]
        trend.append({
            "session": sid,
            "mean_delta": round(sum(vals) / len(vals), 3) if vals else 0,
            "count": len(vals),
        })

    return {
        "skill": "self-audit",
        "workspace": summary.get("workspace", str(knowledge_root)),
        "mode": summary.get("mode", "unknown"),
        "session_id": summary.get("session_id", ""),
        "generated_at": datetime.now().isoformat(timespec="seconds"),
        "kpis": kpis,
        "curve": curve,
        "curve_derived": derived,
        "categories": categories,
        "layers": layers,
        "result_mix": result_mix,
        "trend": trend,
        "blind_spots": blind_spots[:15],
    }


# ---- HTML template: charts drawn as inline SVG in vanilla JS ----
HTML_TEMPLATE = r"""<!doctype html>
<html lang="en">
<head>
<meta charset="utf-8">
<meta name="viewport" content="width=device-width, initial-scale=1">
<title>Self-Audit — Calibration Dashboard</title>
<style>
  .viz-root {
    color-scheme: light;
    --surface-1: #fcfcfb;
    --page: #f9f9f7;
    --text-primary: #0b0b0b;
    --text-secondary: #52514e;
    --muted: #898781;
    --grid: #e1e0d9;
    --baseline: #c3c2b7;
    --border: rgba(11,11,11,0.10);
    --seq-1: #cde2fb; --seq-2: #9ec5f4; --seq-3: #6da7ec; --seq-4: #3987e5;
    --seq-5: #256abf; --seq-6: #1c5cab; --seq-7: #104281;
    --div-neg: #e34948;   /* overconfident (stated > actual) */
    --div-pos: #2a78d6;   /* underconfident (actual > stated) */
    --div-mid: #f0efec;
    --accent: #2a78d6;
    --good: #0ca30c;
  }
  @media (prefers-color-scheme: dark) {
    :root:where(:not([data-theme="light"])) .viz-root {
      color-scheme: dark;
      --surface-1: #1a1a19; --page: #0d0d0d;
      --text-primary: #f0efec; --text-secondary: #c3c2b7; --muted: #898781;
      --grid: #2c2c2a; --baseline: #383835; --border: rgba(255,255,255,0.10);
      --seq-1: #184f95; --seq-2: #256abf; --seq-3: #3987e5; --seq-4: #5598e7;
      --seq-5: #86b6ef; --seq-6: #9ec5f4; --seq-7: #cde2fb;
      --div-neg: #e66767; --div-pos: #3987e5; --div-mid: #383835; --accent: #3987e5;
    }
  }
  :root[data-theme="dark"] .viz-root {
    color-scheme: dark;
    --surface-1: #1a1a19; --page: #0d0d0d;
    --text-primary: #f0efec; --text-secondary: #c3c2b7; --muted: #898781;
    --grid: #2c2c2a; --baseline: #383835; --border: rgba(255,255,255,0.10);
    --seq-1: #184f95; --seq-2: #256abf; --seq-3: #3987e5; --seq-4: #5598e7;
    --seq-5: #86b6ef; --seq-6: #9ec5f4; --seq-7: #cde2fb;
    --div-neg: #e66767; --div-pos: #3987e5; --div-mid: #383835; --accent: #3987e5;
  }
  * { box-sizing: border-box; }
  body {
    margin: 0; background: var(--page, #f9f9f7);
    font-family: system-ui, -apple-system, "Segoe UI", sans-serif;
    color: var(--text-primary, #0b0b0b);
  }
  .viz-root { background: var(--page); min-height: 100vh; padding: 32px 16px 64px; }
  .wrap { max-width: 1080px; margin: 0 auto; }
  header.top { display: flex; align-items: baseline; justify-content: space-between; gap: 16px; flex-wrap: wrap; margin-bottom: 24px; }
  h1 { font-size: 22px; margin: 0; letter-spacing: -0.01em; }
  .sub { color: var(--text-secondary); font-size: 13px; margin-top: 4px; }
  .toggle {
    border: 1px solid var(--border); background: var(--surface-1); color: var(--text-secondary);
    border-radius: 8px; padding: 6px 12px; font-size: 12px; cursor: pointer;
  }
  .kpi-row {
    display: grid; grid-template-columns: repeat(auto-fit, minmax(150px, 1fr));
    gap: 12px; margin-bottom: 28px;
  }
  .tile {
    background: var(--surface-1); border: 1px solid var(--border); border-radius: 12px;
    padding: 16px 18px;
  }
  .tile .label { font-size: 12px; color: var(--text-secondary); }
  .tile .value { font-size: 34px; font-weight: 600; letter-spacing: -0.02em; margin-top: 4px; }
  .tile .value .unit { font-size: 14px; color: var(--muted); font-weight: 400; margin-left: 2px; }
  .panel {
    background: var(--surface-1); border: 1px solid var(--border); border-radius: 12px;
    padding: 18px 20px 8px; margin-bottom: 20px;
  }
  .panel h2 { font-size: 15px; margin: 0 0 2px; letter-spacing: -0.01em; }
  .panel .desc { font-size: 12px; color: var(--text-secondary); margin: 0 0 12px; }
  .grid-2 { display: grid; grid-template-columns: 1fr 1fr; gap: 20px; }
  @media (max-width: 760px) { .grid-2 { grid-template-columns: 1fr; } }
  svg { display: block; width: 100%; height: auto; overflow: visible; }
  .legend { display: flex; flex-wrap: wrap; gap: 12px; margin: 6px 2px 4px; }
  .legend .item { display: flex; align-items: center; gap: 6px; font-size: 12px; color: var(--text-secondary); }
  .legend .swatch { width: 11px; height: 11px; border-radius: 3px; }
  .tooltip {
    position: fixed; pointer-events: none; z-index: 50; opacity: 0;
    background: var(--surface-1); color: var(--text-primary);
    border: 1px solid var(--border); border-radius: 8px; padding: 7px 10px;
    font-size: 12px; box-shadow: 0 4px 16px rgba(0,0,0,0.12); transition: opacity .08s;
    max-width: 240px;
  }
  table.data { width: 100%; border-collapse: collapse; font-size: 12.5px; }
  table.data th, table.data td { text-align: left; padding: 7px 8px; border-bottom: 1px solid var(--grid); }
  table.data th { color: var(--text-secondary); font-weight: 600; }
  table.data td.num { font-variant-numeric: tabular-nums; text-align: right; }
  .note { font-size: 11.5px; color: var(--muted); margin-top: 8px; }
  .axis-label { font-size: 11px; fill: var(--muted); }
  .tick { font-size: 11px; fill: var(--muted); }
  .dlabel { font-size: 11px; fill: var(--text-secondary); font-weight: 600; }
  .hidden { display: none; }
</style>
</head>
<body>
<div class="viz-root">
  <div class="wrap">
    <header class="top">
      <div>
        <h1>Self-Audit — Calibration Dashboard</h1>
        <div class="sub" id="subtitle"></div>
      </div>
      <div style="display:flex; gap:8px;">
        <button class="toggle" id="tableToggle" aria-pressed="false">Show data tables</button>
        <button class="toggle" id="themeToggle">Dark</button>
      </div>
    </header>

    <section class="kpi-row" id="kpiRow"></section>

    <section class="panel">
      <h2>Calibration curve</h2>
      <p class="desc">Actual accuracy vs. the confidence stated, by confidence band. Bars diverge from the well-calibrated midpoint: <strong>red = overconfident</strong> (stated above actual), <strong>blue = underconfident</strong>.</p>
      <div id="curveChart"></div>
      <div class="note" id="curveNote"></div>
    </section>

    <div class="grid-2">
      <section class="panel">
        <h2>Blind spots by category</h2>
        <p class="desc">Count of ranked blind spots per category (magnitude).</p>
        <div id="catChart"></div>
      </section>
      <section class="panel">
        <h2>Assumptions by abstraction layer</h2>
        <p class="desc">Where assumptions concentrate: L1 Syntax → L4 Domain.</p>
        <div id="layerChart"></div>
      </section>
    </div>

    <div class="grid-2">
      <section class="panel">
        <h2>Outcome mix</h2>
        <p class="desc">Calibration test results across the session (part-to-whole).</p>
        <div id="mixChart"></div>
      </section>
      <section class="panel">
        <h2>Calibration trend</h2>
        <p class="desc">Mean |confidence delta| per session — lower is better calibrated.</p>
        <div id="trendChart"></div>
        <div class="note" id="trendNote"></div>
      </section>
    </div>

    <section class="panel hidden" id="tablesPanel">
      <h2>Data tables</h2>
      <div id="tables"></div>
    </section>
  </div>
</div>
<div class="tooltip" id="tooltip"></div>

<script>
const DATA = __PAYLOAD__;
const css = (n) => getComputedStyle(document.querySelector('.viz-root')).getPropertyValue(n).trim();
const tip = document.getElementById('tooltip');
function showTip(evt, html) {
  tip.innerHTML = html; tip.style.opacity = '1';
  const pad = 14;
  let x = evt.clientX + pad, y = evt.clientY + pad;
  const r = tip.getBoundingClientRect();
  if (x + r.width > window.innerWidth - 8) x = evt.clientX - r.width - pad;
  if (y + r.height > window.innerHeight - 8) y = evt.clientY - r.height - pad;
  tip.style.left = x + 'px'; tip.style.top = y + 'px';
}
function hideTip() { tip.style.opacity = '0'; }
function svgEl(tag, attrs) {
  const e = document.createElementNS('http://www.w3.org/2000/svg', tag);
  for (const k in attrs) e.setAttribute(k, attrs[k]);
  return e;
}

// ---- KPI row ----
function renderKpis() {
  const k = DATA.kpis;
  const tiles = [
    ['Assumptions tested', k.tested, ''],
    ['Confirmed', k.confirmed, ''],
    ['Falsified', k.falsified, ''],
    ['Inconclusive', k.inconclusive, ''],
    ['Blind spots', k.blind_spots, ''],
    ['Learning units', k.learning_units, ''],
  ];
  document.getElementById('kpiRow').innerHTML = tiles.map(([label, val]) => (
    `<div class="tile"><div class="label">${label}</div><div class="value">${val}</div></div>`
  )).join('');
}

// ---- Diverging bar: calibration curve ----
function renderCurve() {
  const rows = DATA.curve;
  const host = document.getElementById('curveChart');
  if (!rows.length) {
    host.innerHTML = '<div class="note" style="padding:24px 0;">No calibration records yet — run an audit to populate the curve.</div>';
    return;
  }
  const W = 720, H = 280, m = {t: 20, r: 20, b: 52, l: 46};
  const iw = W - m.l - m.r, ih = H - m.t - m.b;
  const svg = svgEl('svg', {viewBox: `0 0 ${W} ${H}`, role: 'img', 'aria-label': 'Calibration curve'});

  // y: delta from -max..+max, zero at midpoint
  const maxAbs = Math.max(0.2, ...rows.map(r => Math.abs(r.delta)));
  const y = (v) => m.t + ih / 2 - (v / maxAbs) * (ih / 2);
  const zeroY = y(0);

  // gridlines + y ticks
  for (const gv of [-maxAbs, -maxAbs/2, 0, maxAbs/2, maxAbs]) {
    svg.appendChild(svgEl('line', {x1: m.l, x2: W - m.r, y1: y(gv), y2: y(gv),
      stroke: gv === 0 ? css('--baseline') : css('--grid'), 'stroke-width': gv === 0 ? 2 : 1}));
    const t = svgEl('text', {x: m.l - 8, y: y(gv) + 4, 'text-anchor': 'end', class: 'tick'});
    t.textContent = (gv > 0 ? '+' : '') + gv.toFixed(2);
    svg.appendChild(t);
  }

  const bandW = iw / rows.length;
  const barW = Math.min(64, bandW * 0.5);
  rows.forEach((r, i) => {
    const cx = m.l + bandW * i + bandW / 2;
    const x = cx - barW / 2;
    const top = Math.min(y(r.delta), zeroY);
    const h = Math.max(2, Math.abs(y(r.delta) - zeroY));
    const fill = r.delta < -0.02 ? css('--div-neg') : (r.delta > 0.02 ? css('--div-pos') : css('--div-mid'));
    // rounded data-end (4px) anchored to baseline
    const g = svgEl('g', {});
    const path = svgEl('path', {
      d: roundRect(x, top, barW, h, 4, r.delta >= 0 ? 'up' : 'down'),
      fill: fill, stroke: css('--surface-1'), 'stroke-width': 2
    });
    g.appendChild(path);
    // direct value label
    const lab = svgEl('text', {x: cx, y: r.delta >= 0 ? top - 6 : top + h + 15, 'text-anchor': 'middle', class: 'dlabel'});
    lab.textContent = (r.delta > 0 ? '+' : '') + r.delta.toFixed(2);
    g.appendChild(lab);
    // band label
    const bl = svgEl('text', {x: cx, y: H - 30, 'text-anchor': 'middle', class: 'axis-label'});
    bl.textContent = r.band;
    g.appendChild(bl);
    const cnt = svgEl('text', {x: cx, y: H - 16, 'text-anchor': 'middle', class: 'tick'});
    cnt.textContent = `n=${r.count}`;
    g.appendChild(cnt);

    g.style.cursor = 'default';
    g.addEventListener('mousemove', (e) => showTip(e,
      `<strong>${r.band}</strong><br>actual ${(r.actual*100).toFixed(0)}% vs stated ${(r.stated*100).toFixed(0)}%<br>delta ${r.delta>0?'+':''}${r.delta.toFixed(2)} · n=${r.count}`));
    g.addEventListener('mouseleave', hideTip);
    svg.appendChild(g);
  });

  host.innerHTML = '';
  host.appendChild(svg);
  const legend = document.createElement('div');
  legend.className = 'legend';
  legend.innerHTML = `
    <div class="item"><span class="swatch" style="background:${css('--div-neg')}"></span>Overconfident</div>
    <div class="item"><span class="swatch" style="background:${css('--div-pos')}"></span>Underconfident</div>
    <div class="item"><span class="swatch" style="background:${css('--div-mid')}"></span>Well calibrated</div>`;
  host.appendChild(legend);
  document.getElementById('curveNote').textContent = DATA.curve_derived
    ? 'Note: per-record stated confidence was not stored; bands derived from |confidence delta|. Accuracy is measured against CONFIRMED share.'
    : 'Delta = actual accuracy − stated confidence. Bars near zero are well calibrated.';
}

function roundRect(x, y, w, h, r, dir) {
  // rounded only at the data end (away from baseline)
  r = Math.min(r, w / 2, h);
  if (dir === 'up') {
    return `M${x},${y+h} L${x},${y+r} Q${x},${y} ${x+r},${y} L${x+w-r},${y} Q${x+w},${y} ${x+w},${y+r} L${x+w},${y+h} Z`;
  } else {
    return `M${x},${y} L${x},${y+h-r} Q${x},${y+h} ${x+r},${y+h} L${x+w-r},${y+h} Q${x+w},${y+h} ${x+w},${y+h-r} L${x+w},${y} Z`;
  }
}

// ---- Horizontal sequential bars (magnitude) ----
function renderHBars(hostId, rows, ariaLabel) {
  const host = document.getElementById(hostId);
  if (!rows.length) {
    host.innerHTML = '<div class="note" style="padding:16px 0;">No data.</div>';
    return;
  }
  const max = Math.max(...rows.map(r => r.value), 1);
  const rowH = 34, gap = 8, labelW = 168, W = 640;
  const H = rows.length * (rowH + gap) + 16;
  const svg = svgEl('svg', {viewBox: `0 0 ${W} ${H}`, role: 'img', 'aria-label': ariaLabel});
  const seq = ['--seq-4','--seq-5','--seq-3','--seq-6','--seq-2','--seq-7','--seq-1'];
  rows.forEach((r, i) => {
    const y = 8 + i * (rowH + gap);
    const bw = (r.value / max) * (W - labelW - 60);
    const name = svgEl('text', {x: labelW - 10, y: y + rowH/2 + 4, 'text-anchor': 'end', class: 'axis-label'});
    name.textContent = r.name; svg.appendChild(name);
    const rect = svgEl('path', {
      d: roundRect(labelW, y, Math.max(3, bw), rowH - 6, 4, 'up'),
      fill: css(seq[i % seq.length]), stroke: css('--surface-1'), 'stroke-width': 2
    });
    rect.style.cursor = 'default';
    rect.addEventListener('mousemove', (e) => showTip(e, `<strong>${r.name}</strong><br>${r.value}`));
    rect.addEventListener('mouseleave', hideTip);
    svg.appendChild(rect);
    const val = svgEl('text', {x: labelW + Math.max(3, bw) + 8, y: y + rowH/2 + 4, class: 'dlabel'});
    val.textContent = r.value; svg.appendChild(val);
  });
  host.innerHTML = ''; host.appendChild(svg);
}

// ---- Outcome mix (part-to-whole stacked bar) ----
function renderMix() {
  const rows = DATA.result_mix;
  const host = document.getElementById('mixChart');
  if (!rows.length) { host.innerHTML = '<div class="note" style="padding:16px 0;">No data.</div>'; return; }
  const total = rows.reduce((s, r) => s + r.value, 0) || 1;
  const W = 640, H = 92, barY = 16, barH = 40;
  const svg = svgEl('svg', {viewBox: `0 0 ${W} ${H}`, role: 'img', 'aria-label': 'Outcome mix'});
  const colors = ['--seq-5','--div-neg','--seq-2','--seq-1','--seq-3'];
  let x = 0;
  rows.forEach((r, i) => {
    const w = (r.value / total) * W;
    const seg = svgEl('path', {
      d: roundRect(x + 1, barY, Math.max(2, w - 2), barH, 4, 'up'),
      fill: css(colors[i % colors.length]), stroke: css('--surface-1'), 'stroke-width': 2
    });
    seg.style.cursor = 'default';
    seg.addEventListener('mousemove', (e) => showTip(e, `<strong>${r.name}</strong><br>${r.value} (${(r.value/total*100).toFixed(0)}%)`));
    seg.addEventListener('mouseleave', hideTip);
    svg.appendChild(seg);
    if (w > 46) {
      const pct = svgEl('text', {x: x + w/2, y: barY + barH/2 + 4, 'text-anchor': 'middle', class: 'dlabel'});
      pct.textContent = Math.round(r.value/total*100) + '%';
      svg.appendChild(pct);
    }
    x += w;
  });
  host.innerHTML = ''; host.appendChild(svg);
  const legend = document.createElement('div');
  legend.className = 'legend';
  legend.innerHTML = rows.map((r, i) =>
    `<div class="item"><span class="swatch" style="background:${css(colors[i % colors.length])}"></span>${r.name} · ${r.value}</div>`).join('');
  host.appendChild(legend);
}

// ---- Trend line ----
function renderTrend() {
  const rows = DATA.trend;
  const host = document.getElementById('trendChart');
  const note = document.getElementById('trendNote');
  if (rows.length < 2) {
    host.innerHTML = '<div class="note" style="padding:24px 0;">Trend needs ≥2 sessions. Keep running audits to build history.</div>';
    note.textContent = rows.length === 1 ? `Current session mean |delta|: ${rows[0].mean_delta.toFixed(2)}` : '';
    return;
  }
  const W = 640, H = 240, m = {t: 16, r: 20, b: 40, l: 46};
  const iw = W - m.l - m.r, ih = H - m.t - m.b;
  const svg = svgEl('svg', {viewBox: `0 0 ${W} ${H}`, role: 'img', 'aria-label': 'Calibration trend'});
  const maxV = Math.max(...rows.map(r => r.mean_delta), 0.1);
  const x = (i) => m.l + (iw * i) / (rows.length - 1);
  const y = (v) => m.t + ih - (v / maxV) * ih;
  for (let g = 0; g <= 4; g++) {
    const gv = (maxV * g) / 4;
    svg.appendChild(svgEl('line', {x1: m.l, x2: W - m.r, y1: y(gv), y2: y(gv), stroke: css('--grid'), 'stroke-width': 1}));
    const t = svgEl('text', {x: m.l - 8, y: y(gv) + 4, 'text-anchor': 'end', class: 'tick'});
    t.textContent = gv.toFixed(2); svg.appendChild(t);
  }
  const d = rows.map((r, i) => `${i === 0 ? 'M' : 'L'}${x(i)},${y(r.mean_delta)}`).join(' ');
  svg.appendChild(svgEl('path', {d, fill: 'none', stroke: css('--accent'), 'stroke-width': 2, 'stroke-linejoin': 'round', 'stroke-linecap': 'round'}));
  rows.forEach((r, i) => {
    const c = svgEl('circle', {cx: x(i), cy: y(r.mean_delta), r: 5, fill: css('--accent'), stroke: css('--surface-1'), 'stroke-width': 2});
    c.style.cursor = 'default';
    c.addEventListener('mousemove', (e) => showTip(e, `<strong>${r.session}</strong><br>mean |delta| ${r.mean_delta.toFixed(2)} · n=${r.count}`));
    c.addEventListener('mouseleave', hideTip);
    svg.appendChild(c);
    const lab = svgEl('text', {x: x(i), y: H - 14, 'text-anchor': 'middle', class: 'tick'});
    lab.textContent = `S${i + 1}`; svg.appendChild(lab);
    const v = svgEl('text', {x: x(i), y: y(r.mean_delta) - 12, 'text-anchor': 'middle', class: 'dlabel'});
    v.textContent = r.mean_delta.toFixed(2); svg.appendChild(v);
  });
  host.innerHTML = ''; host.appendChild(svg);
  const first = rows[0].mean_delta, last = rows[rows.length - 1].mean_delta;
  const dir = last < first ? 'improving' : last > first ? 'degrading' : 'stable';
  note.textContent = `Direction: ${dir} (mean |delta| ${first.toFixed(2)} → ${last.toFixed(2)}).`;
}

// ---- Data tables (accessibility) ----
function renderTables() {
  const t = document.getElementById('tables');
  const mkTable = (title, cols, rows) => {
    return `<h3 style="font-size:13px;margin:12px 0 6px;">${title}</h3>
      <table class="data"><thead><tr>${cols.map(c => `<th${c.num?' class="num"':''}>${c.label}</th>`).join('')}</tr></thead>
      <tbody>${rows.map(r => `<tr>${cols.map(c => `<td${c.num?' class="num"':''}>${r[c.key]}</td>`).join('')}</tr>`).join('')}</tbody></table>`;
  };
  let html = '';
  if (DATA.curve.length) html += mkTable('Calibration curve',
    [{label:'Band',key:'band'},{label:'Actual',key:'actual',num:true},{label:'Stated',key:'stated',num:true},{label:'Delta',key:'delta',num:true},{label:'N',key:'count',num:true}],
    DATA.curve.map(r => ({...r, actual:(r.actual*100).toFixed(0)+'%', stated:(r.stated*100).toFixed(0)+'%', delta:(r.delta>0?'+':'')+r.delta.toFixed(2)})));
  if (DATA.categories.length) html += mkTable('Blind spots by category', [{label:'Category',key:'name'},{label:'Count',key:'value',num:true}], DATA.categories);
  if (DATA.layers.length) html += mkTable('Assumptions by layer', [{label:'Layer',key:'name'},{label:'Count',key:'value',num:true}], DATA.layers);
  if (DATA.result_mix.length) html += mkTable('Outcome mix', [{label:'Result',key:'name'},{label:'Count',key:'value',num:true}], DATA.result_mix);
  if (DATA.blind_spots.length) html += mkTable('Top blind spots',
    [{label:'Rank',key:'rank',num:true},{label:'ID',key:'id'},{label:'Category',key:'category'},{label:'Layer',key:'layer'},{label:'Severity',key:'severity'},{label:'Delta',key:'delta',num:true}],
    DATA.blind_spots.map(b => ({...b, delta: b.delta === null ? '—' : b.delta.toFixed(2)})));
  t.innerHTML = html || '<div class="note">No data.</div>';
}

// ---- Wiring ----
document.getElementById('subtitle').textContent =
  `${DATA.workspace} · mode ${DATA.mode} · ${DATA.session_id} · generated ${DATA.generated_at}`;
renderKpis(); renderCurve();
renderHBars('catChart', DATA.categories, 'Blind spots by category');
renderHBars('layerChart', DATA.layers, 'Assumptions by layer');
renderMix(); renderTrend(); renderTables();

const tgl = document.getElementById('tableToggle');
tgl.addEventListener('click', () => {
  const p = document.getElementById('tablesPanel');
  const open = p.classList.toggle('hidden') === false;
  tgl.setAttribute('aria-pressed', String(open));
  tgl.textContent = open ? 'Hide data tables' : 'Show data tables';
});
const themeBtn = document.getElementById('themeToggle');
themeBtn.addEventListener('click', () => {
  const cur = document.documentElement.getAttribute('data-theme');
  const next = cur === 'dark' ? 'light' : (cur === 'light' ? 'dark' : (matchMedia('(prefers-color-scheme: dark)').matches ? 'light' : 'dark'));
  document.documentElement.setAttribute('data-theme', next);
  themeBtn.textContent = next === 'dark' ? 'Light' : 'Dark';
  // re-render charts to pick up swapped CSS variables
  renderCurve(); renderHBars('catChart', DATA.categories, 'Blind spots by category');
  renderHBars('layerChart', DATA.layers, 'Assumptions by layer'); renderMix(); renderTrend();
});
window.addEventListener('resize', () => {
  renderCurve(); renderHBars('catChart', DATA.categories, 'Blind spots by category');
  renderHBars('layerChart', DATA.layers, 'Assumptions by layer'); renderMix(); renderTrend();
});
</script>
</body>
</html>
"""


def generate(knowledge_root: Path, output: Path = None) -> Path:
    payload = build_payload(knowledge_root)
    html = HTML_TEMPLATE.replace("__PAYLOAD__", json.dumps(payload, ensure_ascii=False))
    output = output or (knowledge_root / "dashboard.html")
    output.write_text(html, encoding="utf-8")
    return output


def main():
    parser = argparse.ArgumentParser(description="Generate a self-contained self-audit dashboard.html")
    parser.add_argument("--knowledge-root", default=os.getenv("SELF_AUDIT_KNOWLEDGE_ROOT", ".claude/knowledge"))
    parser.add_argument("--output", default=None)
    args = parser.parse_args()

    root = Path(args.knowledge_root).resolve()
    if not root.exists():
        print(f"Knowledge root not found: {root}")
        raise SystemExit(1)
    out = generate(root, Path(args.output).resolve() if args.output else None)
    print(f"Dashboard written to: {out}")


if __name__ == "__main__":
    main()