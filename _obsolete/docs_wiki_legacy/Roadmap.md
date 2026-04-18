# Roadmap

## Status (April 2026)

| ID | Task | Status | Notes |
|----|------|--------|-------|
| P0 | Expand Java GT to n≥50 | ✅ DONE | n=59, commit b336496 |
| P1 | Jolak cross-validation | ✅ DONE | 4/5 CONFIRMED |
| P2 | god_class_ratio investigation | ✅ DONE | Not adding to formula |
| P3 | Django false-negative analysis | ✅ DONE | Needs better detection |
| P4 | Re-run Java-S on expanded GT | ✅ DONE | v3c confirmed, S-monotonicity broken |

## Completed Milestones

### P0 — Java GT Expansion
- Scanned 30 candidate repos (12 POS, 8 NEG, 10 UNCLEAR expected)
- Expert panel rated all 30 (final: 16 POS, 14 NEG)
- Merged with original GT (n=29) → expanded GT (n=59)
- All statistics remain highly significant (MW p=0.0002)

### P1 — Jolak Cross-Validation
- Built pure-Python Java scanner (tree-sitter-java)
- Fixed critical granularity bug (package-level → file-level nodes)
- 8/8 repos scanned, 4/5 findings confirmed

### P2 — god_class_ratio
- Investigated but decided not to add to formula
- No sufficient justification for new metric

### P3 — Django False-Negative
- Django scores NEG despite being well-architected
- Root cause: scanner needs better intra-package detection
- Deferred — not blocking main line of work

### P4 — Re-run Java-S on Expanded GT
- 18 weight variants tested on n=59 GT
- v3c (equal 0.20 weights) CONFIRMED as winner
- S-weight monotonicity broken: inverted-U curve, peak at S=0.20
- Original ρ=1.00 was small-sample artifact (n=29), now ρ=0.00 (n=59)
- Split-half instability: all variants unstable — landscape is flat
- Recommendation: close weight optimization

### Full Plan Execution (April 2026)
- Strict GT created: n=38 (20 POS, 18 NEG) with protocol-compliant filters
- Java-S variants on strict GT: v3c confirmed, C_boost best but within CI
- Python Type E: god-module metrics correct direction but ns
- Updated Claims & Evidence (v3.0) + Threats to Validity (v3.0)
- Test Architecture v1 spec written (thresholds, FF1-FF3)
- qse-archtest CLI built + GitHub Action workflows
- Pilot plan template created (OSS + internal)
- Python GT candidates (15 repos) identified for expansion

## Future Work

- Expand Python GT beyond n=30 (15 candidates ready)
- Utility library normalization for CD
- Architecture category stratification
- Cross-language formula unification (Java + Python)
- GT expansion to n>200 (if weight discrimination needed)
- Explore 6th component with novel discriminative power
- Run OSS + internal pilots with qse-archtest

## Git History (perplexity branch)

| Commit | Description |
|--------|-------------|
| 3cb9713 | feat: full plan — docs, CLI, Action, strict GT, pilot template |
| (prev) | feat: P4 Java-S experiment results |
| b336496 | feat: expanded Java GT to n=59 |
| aa85608 | feat: pure-Python Java scanner + Jolak cross-validation |
| d4589d2 | (remote sync) |
| ... | Earlier commits |
