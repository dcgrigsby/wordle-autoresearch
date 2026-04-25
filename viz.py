"""Generate a static HTML dashboard from autoresearch/log.jsonl.

Reads:
  - autoresearch/log.jsonl
  - autoresearch/experiments/NNN.diff

Writes:
  - autoresearch/dashboard.html  (open in any browser; no JS or CDN deps)

DO NOT MODIFY during the autoresearch loop.
"""
import html
import json
from pathlib import Path

ROOT = Path(__file__).parent
AR = ROOT / "autoresearch"
LOG = AR / "log.jsonl"
EXP_DIR = AR / "experiments"
OUT = AR / "dashboard.html"


def load_log():
    if not LOG.exists():
        return []
    return [json.loads(line) for line in LOG.read_text().splitlines() if line.strip()]


def svg_chart(experiments, w=900, h=320, pad=50):
    metrics = [e.get("metric") for e in experiments]
    bests = [e.get("best") for e in experiments]
    valid = [m for m in metrics if m is not None]
    if not valid:
        return "<p><em>no scored experiments yet</em></p>"

    all_vals = valid + [b for b in bests if b is not None]
    ymin, ymax = min(all_vals), max(all_vals)
    yrange = max(ymax - ymin, 0.1)
    ymin -= yrange * 0.1
    ymax += yrange * 0.1
    yrange = ymax - ymin

    n = len(experiments)

    def x(i): return pad + (w - 2 * pad) * (i / max(n - 1, 1))
    def y(v): return h - pad - (h - 2 * pad) * ((v - ymin) / yrange)

    parts = [f'<svg viewBox="0 0 {w} {h}" xmlns="http://www.w3.org/2000/svg" '
             f'style="background:#fafafa;border:1px solid #ddd;border-radius:4px;width:100%;height:auto">']

    for frac in [0, 0.25, 0.5, 0.75, 1.0]:
        gy = pad + (h - 2 * pad) * frac
        val = ymax - frac * yrange
        parts.append(f'<line x1="{pad}" y1="{gy}" x2="{w-pad}" y2="{gy}" stroke="#eee"/>')
        parts.append(f'<text x="8" y="{gy+4}" font-size="10" fill="#999">{val:.3f}</text>')

    pts = " ".join(f"{x(i)},{y(b)}" for i, b in enumerate(bests) if b is not None)
    if pts:
        parts.append(f'<polyline points="{pts}" fill="none" stroke="#1f77b4" stroke-width="2"/>')

    for i, e in enumerate(experiments):
        m = e.get("metric")
        if m is None:
            continue
        decision = e.get("decision", "")
        color = {"kept": "#2ca02c", "reverted": "#d62728", "baseline": "#1f77b4"}.get(decision, "#888")
        title = f'#{e.get("exp", i)}: {e.get("hypothesis", "")} → {m:.4f} ({decision})'
        parts.append(f'<circle cx="{x(i):.1f}" cy="{y(m):.1f}" r="4" fill="{color}">'
                     f'<title>{html.escape(title)}</title></circle>')

    parts.append(f'<text x="{w/2}" y="{h-10}" text-anchor="middle" font-size="11" fill="#666">'
                 f'experiment # (hover dots for details)</text>')
    parts.append('</svg>')
    return '\n'.join(parts)


def histogram_bars(hist, color="#1f77b4"):
    if not hist:
        return "<p><em>no data</em></p>"
    maxv = max(hist.values()) or 1
    rows = []
    for k, v in hist.items():
        pct = v / maxv * 100
        rows.append(
            f'<div style="display:flex;align-items:center;gap:8px;margin:3px 0;font-size:12px">'
            f'<span style="width:24px;color:#666;text-align:right">{k}</span>'
            f'<div style="background:{color};height:16px;width:{pct}%;min-width:1px;border-radius:2px"></div>'
            f'<span style="color:#666">{v}</span></div>'
        )
    return ''.join(rows)


def render_diff(diff_text):
    if not diff_text:
        return '<em style="color:#999">no diff captured</em>'
    lines = []
    for line in diff_text.splitlines():
        if line.startswith('+++') or line.startswith('---') or line.startswith('@@') or line.startswith('diff'):
            color = "#888"
        elif line.startswith('+'):
            color = "#2ca02c"
        elif line.startswith('-'):
            color = "#d62728"
        else:
            color = "#444"
        lines.append(f'<span style="color:{color}">{html.escape(line)}</span>')
    return ('<pre style="font-size:11px;line-height:1.4;background:#f8f8f8;'
            'padding:10px;border-radius:4px;overflow-x:auto;margin:6px 0">'
            + '\n'.join(lines) + '</pre>')


def main():
    experiments = load_log()

    if not experiments:
        OUT.write_text("<html><body><h1>No experiments yet</h1><p>Run <code>python run_experiment.py '...'</code></p></body></html>")
        print(f"wrote {OUT} (empty)")
        return

    baseline = experiments[0]
    scored = [e for e in experiments if e.get("metric") is not None]
    best = min(scored, key=lambda e: e["metric"]) if scored else baseline

    kept = [e for e in experiments if e.get("decision") == "kept"]
    reverted = [e for e in experiments if e.get("decision") == "reverted"]
    delta = baseline["metric"] - best["metric"] if baseline.get("metric") and best.get("metric") else 0

    rows = []
    for e in reversed(experiments):
        exp_n = e.get("exp", "?")
        decision = e.get("decision", "?")
        badge = {"kept": "#2ca02c", "reverted": "#d62728", "baseline": "#1f77b4"}.get(decision, "#888")
        diff_path = EXP_DIR / f"{exp_n:03d}.diff" if isinstance(exp_n, int) else None
        diff_text = diff_path.read_text() if diff_path and diff_path.exists() else ""
        metric_str = f'{e["metric"]:.4f}' if e.get("metric") is not None else '—'
        best_str = f'{e["best"]:.4f}' if e.get("best") is not None else '—'

        rows.append(f'''
<details style="margin:6px 0;border:1px solid #ddd;border-radius:4px;padding:8px;background:white">
  <summary style="cursor:pointer;display:flex;gap:10px;align-items:center;font-size:13px">
    <span style="background:{badge};color:white;padding:2px 8px;border-radius:3px;font-size:11px;font-weight:600;font-family:monospace">#{exp_n}</span>
    <span style="background:#f0f0f0;padding:2px 7px;border-radius:3px;font-size:11px;color:#444">{decision}</span>
    <span style="color:#222;flex:1">{html.escape(e.get("hypothesis", ""))}</span>
    <span style="font-family:monospace;color:#666;font-size:12px">m={metric_str} best={best_str}</span>
  </summary>
  <div style="padding:10px 4px 4px;color:#555;font-size:12px">
    <div><strong>Reason:</strong> {html.escape(e.get("reason", "—"))}</div>
    {render_diff(diff_text)}
  </div>
</details>''')

    out = f'''<!doctype html>
<html><head>
<meta charset="utf-8">
<title>Wordle autoresearch — dashboard</title>
<style>
body {{ font-family: -apple-system, BlinkMacSystemFont, system-ui, sans-serif; max-width: 1100px; margin: 24px auto; padding: 0 20px; color: #222; line-height: 1.5; }}
h1, h2 {{ font-weight: 500; margin-top: 28px; }}
h1 {{ font-size: 22px; margin-top: 0; }}
h2 {{ font-size: 16px; color: #444; }}
.stats {{ display: flex; gap: 28px; flex-wrap: wrap; margin: 16px 0 24px; }}
.stat .num {{ font-size: 26px; font-weight: 600; line-height: 1.1; }}
.stat .lbl {{ font-size: 11px; color: #888; text-transform: uppercase; letter-spacing: 0.5px; }}
.grid {{ display: grid; grid-template-columns: 1fr 1fr; gap: 24px; }}
code {{ font-family: ui-monospace, monospace; font-size: 12px; background: #f3f3f3; padding: 1px 5px; border-radius: 3px; }}
</style>
</head><body>

<h1>Wordle autoresearch</h1>
<p style="color:#666;font-size:13px">Lower <code>avg_guesses</code> is better. Failures (>6 guesses) count as 7. Eval set: 2,314 official answers.</p>

<div class="stats">
  <div class="stat"><div class="num">{baseline.get("metric", 0):.3f}</div><div class="lbl">baseline</div></div>
  <div class="stat"><div class="num" style="color:#2ca02c">{best.get("metric", 0):.3f}</div><div class="lbl">best</div></div>
  <div class="stat"><div class="num" style="color:{'#2ca02c' if delta > 0 else '#888'}">−{delta:.3f}</div><div class="lbl">improvement</div></div>
  <div class="stat"><div class="num">{len(experiments)-1}</div><div class="lbl">experiments</div></div>
  <div class="stat"><div class="num" style="color:#2ca02c">{len(kept)}</div><div class="lbl">kept</div></div>
  <div class="stat"><div class="num" style="color:#d62728">{len(reverted)}</div><div class="lbl">reverted</div></div>
</div>

<h2>Metric over time</h2>
{svg_chart(experiments)}

<div class="grid" style="margin-top:24px">
  <div>
    <h2>Best — guess distribution</h2>
    {histogram_bars(best.get("histogram", {}), "#2ca02c")}
  </div>
  <div>
    <h2>Baseline — guess distribution</h2>
    {histogram_bars(baseline.get("histogram", {}), "#888")}
  </div>
</div>

<h2>Experiment log <span style="font-size:13px;color:#888;font-weight:normal">(newest first; click to expand diff)</span></h2>
{''.join(rows)}

</body></html>'''

    OUT.write_text(out)
    print(f"wrote {OUT}")


if __name__ == "__main__":
    main()
