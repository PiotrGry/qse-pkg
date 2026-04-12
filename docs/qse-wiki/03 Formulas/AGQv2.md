---
type: formula
status: active-experiment
languages: [java]
components: [M, A, S, C, CD]
---

# AGQv2

## Beginner summary

AGQv2 is a newer formula that improved on AGQv1 by adding one more signal: [[CD]].

In simple words, the goal was to better capture how tangled the project structure is.

This formula works credibly for Java, but it should not be treated as a universal formula for every language.

## Formula

`0.20 M + 0.20 A + 0.35 S + 0.05 C + 0.20 CD`

## What changed from AGQv1

- [[Stability]] got a smaller weight.
- [[CD]] was added.
- The formula became better at separating better and worse Java architectures.

## Notes

- Valid for Java.
- Not a cross-language metric.

## Read next

- [[E2 Coupling Density]]
- [[W4 AGQv2 Beats AGQv1 on Java GT]]
