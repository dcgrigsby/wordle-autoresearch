"""Wordle solver — THE EDITABLE SURFACE for autoresearch.

This is the ONLY file the autoresearch loop may modify.

Required interface (do not change the method names or signatures):
  - Solver()                              — construct
  - new_game() -> state                   — fresh game state
  - next_guess(state) -> str              — return a 5-letter lowercase guess
  - update(state, guess, feedback) -> state  — incorporate feedback (G/Y/B string)

Baseline strategy: fixed opener "crane", then greedy pick from remaining
candidate answers by sum of unique-letter frequencies. Expected baseline
average: ~4.0–4.2 guesses on the 2,314-answer set.
"""
import math
from collections import Counter
from pathlib import Path

from eval import score_guess

DATA = Path(__file__).parent / "data"


class Solver:
    def __init__(self):
        self.answers = [w.strip() for w in (DATA / "answers.txt").read_text().splitlines() if w.strip()]
        guesses = [w.strip() for w in (DATA / "guesses.txt").read_text().splitlines() if w.strip()]
        self.allowed = list(set(self.answers) | set(guesses))

    def new_game(self):
        return {"candidates": list(self.answers), "turn": 0}

    def next_guess(self, state):
        cands = state["candidates"]
        if state["turn"] == 0:
            return "salet"
        if len(cands) == 1:
            return cands[0]
        n = len(cands)
        best_word, best_entropy = None, -1.0
        for guess in cands:
            patterns = Counter()
            for ans in cands:
                patterns[score_guess(guess, ans)] += 1
            entropy = sum(-(c / n) * math.log2(c / n) for c in patterns.values())
            if entropy > best_entropy:
                best_entropy = entropy
                best_word = guess
        return best_word

    def update(self, state, guess, feedback):
        new_cands = [w for w in state["candidates"] if score_guess(guess, w) == feedback]
        return {"candidates": new_cands, "turn": state["turn"] + 1}
