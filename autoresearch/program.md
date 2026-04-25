# Wordle solver — autoresearch program

## Goal

Minimize the average number of guesses a Wordle solver takes to solve every
official answer. Reach the human-tuned floor (~3.42) or get as close as
compounding small improvements allows.

## The triplet

### Editable surface
`solver.py` (one file). The agent may modify the `Solver` class implementation
but **not** the public method names or signatures (`new_game`, `next_guess`,
`update`). All other files are read-only.

### Metric
`avg_guesses` from `eval.py`, computed over all 2,314 answers in
`data/answers.txt`. Failures (> 6 turns) count as 7. **Lower is better.**

Strict-improvement rule: a new candidate is kept only if its `avg_guesses` is
strictly less than the current best. Ties revert.

Secondary metrics (logged but not optimized for): `success_rate`, `histogram`,
`elapsed_s`. Watch these in the debrief — a "win" that crashes success rate
or pushes runtime past the budget is a red flag.

### Time budget
60 seconds per experiment (full eval). The current baseline runs in seconds.
Anything that pushes past 60s is implicitly disqualified — that constraint
prevents "win by exhaustive search" hypotheses that aren't real strategy
improvements.

## Per-experiment workflow

1. Read `solver.py` and the last few entries in `log.jsonl` for context.
2. Form **one** hypothesis. Edit `solver.py` to express it.
3. Run: `python run_experiment.py "<one-line hypothesis>"`
4. The wrapper handles diff capture, scoring, keep/revert decision, log
   append, and dashboard regeneration. Read its output and decide the next
   hypothesis.

## Direction — hypotheses worth trying

Roughly ordered by expected payoff:

- **Better opener.** "crane" is decent but not optimal. Search the answer set
  for openers that minimize expected remaining-candidate count after one turn.
  Known strong openers: "soare", "raise", "salet", "tares", "crate".
- **Information-theoretic guess scoring.** Replace letter-frequency greedy
  with: pick the guess that maximizes expected information (entropy) over the
  remaining candidate distribution. This is the single biggest known lever.
- **Allow guesses outside the candidate set.** Sometimes a non-candidate word
  splits the candidates better than any candidate does. Use the full ~12,970
  guess pool, not just remaining answers.
- **Endgame switch.** When `len(candidates) <= K`, just pick from candidates
  (avoid wasted information turns). Tune K.
- **Two-step lookahead.** For small remaining sets, evaluate guess pairs.
- **Tie-breaking by answer likelihood.** Rare-letter words are less likely
  answers — bias toward common-letter words on the final guess.
- **Cache feedback patterns.** `score_guess` is called many times; precompute
  a `(guess, answer) -> pattern` table for the hot subset.

## Anti-patterns / metric-gaming watchlist

Pre-mortem: ways the metric could move without the solver actually getting
smarter. Flag any of these in review.

- **Hardcoding answers.** A solver that special-cases specific answer strings
  is overfitting to the public list, not playing Wordle. Reject any diff that
  embeds answer strings as literal cases.
- **Reading the answer.** Any code path that consults the true answer outside
  of `eval.score_guess` feedback is cheating. The `Solver` class never
  receives the answer.
- **Modifying the eval or data files.** Out of scope. Reject and revert.
- **Bypassing the time budget by precomputing at import time.** A 5-minute
  `__init__` that pretends "the solver is fast" is gaming the per-experiment
  timer. Watch `elapsed_s` plus solver instantiation time.
- **Crashing on rare answers but counting them as 6.** A failure must count
  as 7 (penalty), and `eval.py` enforces this — don't let the solver swallow
  exceptions and return arbitrary words.
- **Optimizing for the public answer list at the expense of generalization.**
  The 2,314-word list is public, finite, and the metric is computed over it,
  so this is a real risk. Self-reflection check on every kept change: "would
  this still help on a held-out 500-answer set?" If "no", flag it.

## Stopping conditions

- 30 experiments without an improvement (plateau)
- 100 total experiments (cap)
- Suspicion: any anti-pattern triggered
- Reaching `avg_guesses <= 3.45` (near the known floor — diminishing returns)

## Debrief deliverable

When the loop stops, write `autoresearch/report.md` covering:
baseline → best, kept changes ranked by contribution, surprising findings,
anti-pattern watch, and a recommendation (promote / another round / revise
the triplet).
