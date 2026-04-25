# Wordle autoresearch

Autonomous optimization loop for a Wordle solver. The agent edits one file
(`solver.py`), runs an objective scorer (`eval.py`), and keeps changes only
when the metric strictly improves.

## Layout

```
solver.py                    # EDITABLE SURFACE — the only file the loop modifies
eval.py                      # read-only scorer; defines the metric
run_experiment.py            # wrapper: diff → eval → keep/revert → log → viz
viz.py                       # regenerates autoresearch/dashboard.html
data/answers.txt             # 2,314 official Wordle answers
data/guesses.txt             # 10,656 additional valid guesses
autoresearch/program.md      # the triplet + constraints + gaming watchlist
autoresearch/log.jsonl       # one JSON entry per experiment
autoresearch/experiments/    # NNN.diff for each attempted change
autoresearch/dashboard.html  # human-readable visualizer
```

## How to use

Baseline:
```
uv run eval.py
```

One experiment (after editing `solver.py`):
```
uv run run_experiment.py "use entropy maximization for guess 2+"
```

View progress:
```
open autoresearch/dashboard.html
```

## Metric

`avg_guesses` over all 2,314 answers. Failures (> 6 turns) count as 7.
Lower is better. Known floor with full lookahead: ~3.42.

## License & Warranty

This project was created by [Claude Code](https://claude.com/claude-code) and is
distributed under the Apache 2.0 License. See the `LICENSE` file for full details.

**Important:** This project comes with **no warranty**. It is provided "as is" without
any guarantees of merchantability, fitness for a particular purpose, or correctness.
You are solely responsible for determining the appropriateness of using this software
and assume all risks associated with its use. See the Apache 2.0 License for complete
terms and liability limitations.
