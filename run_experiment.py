"""Run one autoresearch experiment.

Usage: python run_experiment.py "<hypothesis>"

The agent's workflow per experiment:
  1. Edit solver.py (uncommitted change)
  2. Run: python run_experiment.py "what I tried and why"
  3. This script: captures the diff, runs eval, decides keep/revert, commits or
     reverts, appends log.jsonl, regenerates dashboard.html.

Keep/revert rule: strictly less avg_guesses than the current best. Ties revert
(we don't want drift on noise-free metrics).

DO NOT MODIFY this file during the autoresearch loop.
"""
import json
import subprocess
import sys
import time
from pathlib import Path

ROOT = Path(__file__).parent
AR = ROOT / "autoresearch"
LOG = AR / "log.jsonl"
EXP = AR / "experiments"


def sh(cmd, check=False):
    r = subprocess.run(cmd, shell=True, cwd=ROOT, capture_output=True, text=True)
    if check and r.returncode != 0:
        sys.stderr.write(r.stderr)
        sys.exit(r.returncode)
    return r.stdout.strip(), r.returncode


def load_log():
    if not LOG.exists():
        return []
    return [json.loads(line) for line in LOG.read_text().splitlines() if line.strip()]


def append_log(entry):
    LOG.parent.mkdir(parents=True, exist_ok=True)
    with LOG.open("a") as f:
        f.write(json.dumps(entry) + "\n")


def best_so_far(log):
    scored = [e for e in log if e.get("metric") is not None]
    return min(scored, key=lambda e: e["metric"]) if scored else None


def main():
    if len(sys.argv) < 2:
        sys.stderr.write("usage: run_experiment.py '<hypothesis>'\n")
        sys.exit(2)
    hypothesis = sys.argv[1]

    diff, _ = sh("git diff HEAD -- solver.py")
    if not diff:
        sys.stderr.write("no uncommitted changes to solver.py — nothing to test\n")
        sys.exit(2)

    log = load_log()
    exp_n = max((e.get("exp", -1) for e in log), default=-1) + 1
    EXP.mkdir(parents=True, exist_ok=True)
    (EXP / f"{exp_n:03d}.diff").write_text(diff)

    print(f"=== experiment #{exp_n}: {hypothesis} ===")
    out, code = sh("uv run eval.py")
    print(out)

    bsf = best_so_far(log)
    bsf_metric = bsf["metric"] if bsf else float("inf")

    if code != 0:
        sh("git checkout -- solver.py")
        append_log({
            "ts": time.strftime("%Y-%m-%dT%H:%M:%S"),
            "exp": exp_n,
            "hypothesis": hypothesis,
            "metric": None,
            "best": bsf_metric if bsf else None,
            "decision": "reverted",
            "reason": "eval crashed (non-zero exit)",
        })
        sh("uv run viz.py")
        sys.exit(1)

    try:
        result = json.loads(out)
    except json.JSONDecodeError as e:
        sh("git checkout -- solver.py")
        append_log({
            "ts": time.strftime("%Y-%m-%dT%H:%M:%S"),
            "exp": exp_n,
            "hypothesis": hypothesis,
            "metric": None,
            "best": bsf_metric if bsf else None,
            "decision": "reverted",
            "reason": f"eval output not JSON-parseable: {e}",
        })
        sh("uv run viz.py")
        sys.exit(1)

    metric = result["avg_guesses"]

    if metric < bsf_metric:
        commit_msg = f"exp #{exp_n}: {hypothesis} ({metric:.4f})"
        sh(f"git add solver.py && git commit -m {json.dumps(commit_msg)}", check=True)
        decision = "kept"
        new_best = metric
        reason = f"improved {bsf_metric:.4f} → {metric:.4f}"
    else:
        sh("git checkout -- solver.py")
        decision = "reverted"
        new_best = bsf_metric
        reason = f"no improvement ({metric:.4f} vs best {bsf_metric:.4f})"

    entry = {
        "ts": time.strftime("%Y-%m-%dT%H:%M:%S"),
        "exp": exp_n,
        "hypothesis": hypothesis,
        "metric": metric,
        "best": new_best,
        "success_rate": result["success_rate"],
        "failures": result["failures"],
        "histogram": result["histogram"],
        "elapsed_s": result["elapsed_s"],
        "decision": decision,
        "reason": reason,
    }
    append_log(entry)
    sh("uv run viz.py")
    print(f"=> {decision}: {reason}")


if __name__ == "__main__":
    main()
