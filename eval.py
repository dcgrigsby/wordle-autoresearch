"""Wordle solver eval harness — read-only scorer.

DO NOT MODIFY during the autoresearch loop. The agent edits solver.py only;
everything in this file defines the metric and is part of the contract.

Runs the solver against every official Wordle answer. Prints JSON with:
  - avg_guesses   : primary metric, lower is better. Failures count as 7.
  - success_rate  : fraction solved in <= 6 guesses
  - failures      : count of answers that took > 6 guesses
  - histogram     : guesses distribution {1..6, 7+}
  - elapsed_s     : wall-clock seconds for the full eval
  - worst_20      : the 20 hardest answers (for inspection only — not part of the metric)
"""
import json
import time
from pathlib import Path

ROOT = Path(__file__).parent
DATA = ROOT / "data"


def score_guess(guess: str, answer: str) -> str:
    """Return 5-char feedback string of G/Y/B (green/yellow/black-aka-gray).

    Handles duplicate letters correctly: greens claim positions first, then yellows
    consume remaining answer-letter counts in left-to-right order.
    """
    result = ['B'] * 5
    answer_chars = list(answer)
    for i in range(5):
        if guess[i] == answer[i]:
            result[i] = 'G'
            answer_chars[i] = None
    for i in range(5):
        if result[i] == 'B' and guess[i] in answer_chars:
            result[i] = 'Y'
            answer_chars[answer_chars.index(guess[i])] = None
    return ''.join(result)


def play(answer: str, solver) -> int:
    """Returns turns_used. Values > 6 mean failure (the game cap is 6 in real Wordle)."""
    state = solver.new_game()
    for turn in range(1, 10):
        guess = solver.next_guess(state)
        if len(guess) != 5 or not guess.isalpha():
            raise ValueError(f"solver returned invalid guess {guess!r} on answer {answer!r}")
        feedback = score_guess(guess, answer)
        if guess == answer:
            return turn
        state = solver.update(state, guess, feedback)
    return 10  # solver couldn't finish even within 9 turns


def main():
    from solver import Solver
    answers = [w.strip() for w in (DATA / "answers.txt").read_text().splitlines() if w.strip()]
    solver = Solver()

    t0 = time.time()
    total = 0.0
    failures = 0
    histogram = [0] * 8  # index 1..7 used
    per_word = []

    for ans in answers:
        turns = play(ans, solver)
        scored = turns if turns <= 6 else 7
        total += scored
        if turns > 6:
            failures += 1
        histogram[min(turns, 7)] += 1
        per_word.append((ans, turns))

    elapsed = time.time() - t0
    avg = total / len(answers)
    success_rate = 1 - failures / len(answers)
    worst = sorted(per_word, key=lambda x: -x[1])[:20]

    result = {
        "avg_guesses": round(avg, 4),
        "success_rate": round(success_rate, 4),
        "failures": failures,
        "n_answers": len(answers),
        "histogram": dict(zip(["1", "2", "3", "4", "5", "6", "7+"], histogram[1:])),
        "elapsed_s": round(elapsed, 2),
        "worst_20": worst,
    }
    print(json.dumps(result, indent=2))
    return result


if __name__ == "__main__":
    main()
