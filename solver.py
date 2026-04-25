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


def _pattern_int(guess, answer):
    """Wordle feedback encoded as int 0..242 (base-3, B=0 Y=1 G=2). Same algorithm as eval.score_guess."""
    a = list(answer)
    greens = [False] * 5
    for i in range(5):
        if guess[i] == a[i]:
            greens[i] = True
            a[i] = '_'
    p = 0
    for i in range(5):
        if greens[i]:
            p = p * 3 + 2
        elif guess[i] in a:
            p = p * 3 + 1
            a[a.index(guess[i])] = '_'
        else:
            p = p * 3
    return p


class Solver:
    def __init__(self):
        self.answers = [w.strip() for w in (DATA / "answers.txt").read_text().splitlines() if w.strip()]
        guesses = [w.strip() for w in (DATA / "guesses.txt").read_text().splitlines() if w.strip()]
        self.allowed = list(set(self.answers) | set(guesses))
        self._answer_idx = {w: i for i, w in enumerate(self.answers)}
        # Precompute (answer, answer) pattern table so entropy compute is a list lookup
        self._pattern_table = {
            g: [_pattern_int(g, a) for a in self.answers]
            for g in self.answers
        }

    def new_game(self):
        return {"candidates": list(self.answers), "turn": 0}

    def next_guess(self, state):
        cands = state["candidates"]
        if state["turn"] == 0:
            return "salet"
        if len(cands) == 1:
            return cands[0]
        n = len(cands)
        cand_indices = [self._answer_idx[w] for w in cands]
        cand_set = set(cands)
        # Mid-range: scan all answers, not just remaining candidates, so we can
        # pick a non-candidate "splitter" word when the cands share too many letters
        pool = self.answers if 2 < n <= 30 else cands
        best_word, best_key = None, None
        for guess in pool:
            row = self._pattern_table[guess]
            patterns = Counter()
            for i in cand_indices:
                patterns[row[i]] += 1
            entropy = sum(-(c / n) * math.log2(c / n) for c in patterns.values())
            # Tiebreak: prefer guesses that are themselves candidates (1/n win chance this turn)
            key = (entropy, 1 if guess in cand_set else 0)
            if best_key is None or key > best_key:
                best_key = key
                best_word = guess
        return best_word

    def update(self, state, guess, feedback):
        new_cands = [w for w in state["candidates"] if score_guess(guess, w) == feedback]
        return {"candidates": new_cands, "turn": state["turn"] + 1}
