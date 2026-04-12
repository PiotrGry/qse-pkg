---
type: formula
status: immutable
languages: [java, python]
components: [M, A, S, C]
---

# AGQv1

## Beginner summary

AGQv1 is the **original baseline formula** in QSE.

In simple terms, it is the first main recipe QSE used to turn structure signals into one architecture score.

It is still kept as an important reference point, even though later research found problems with some of its weighting choices.

## Formula

`0.20 M + 0.20 A + 0.55 S + 0.05 C`

## What the parts mean

- [[Modularity]]: are parts clearly separated?
- [[Acyclicity]]: are there circular dependencies?
- [[Stability]]: are important parts dependable?
- [[Cohesion]]: do grouped things belong together?

## Notes

- Baseline reference formula.
- Must never be modified.
- Calibrated on [[BLT]], which is a refuted [[Ground Truth]].

## Why it still matters

Even if AGQv1 is not the best current formula, it helps compare new ideas against the original starting point.
