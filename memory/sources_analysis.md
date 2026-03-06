# Analiza źródeł — papiers/sources (2026-03-05)

## 1. Sabra et al. — Assessing Quality & Security (2508.14727) ⭐⭐⭐

**Autorzy:** Abbas Sabra, Olivier Schmitt, Joseph Tyler (Sonar)
**Setup:** 4442 Java zadań × 5 LLM (Claude Sonnet 4, Claude 3.7, GPT-4o, Llama 3.2 90B, OpenCoder-8B), SonarQube ~550 reguł

**Główny wynik (RQ4):**
> "No direct correlation between Pass@1 and overall quality/security of generated code"

**Konkretne liczby (Table 2):**
| Model | Pass@1 | Issues/passing task |
|---|---|---|
| Claude Sonnet 4 | 77.04% (najlepszy) | 2.11 (najgorszy) |
| OpenCoder-8B | 60.43% (najgorszy) | 1.45 (najlepszy) |

**Paradoks Claude 3.7 → Sonnet 4:**
- Pass@1: 72.46% → 77.04% (poprawa)
- BLOCKER bugs: 7.1% → 13.71% (prawie 2×)
- BLOCKER vulnerabilities: 56.03% → 59.57%

**Rozkład defektów (Table 4, wszystkie modele):**
- Code smells: ~90-93%
- Bugs: ~5-8%
- Vulnerabilities: ~2%

**Top code smells (Table 9):**
- Dead/Unused/Redundant code: 14-43% (zależy od modelu)
- Design/Framework best practices: 11-22%
- Cognitive complexity: 4-8%

**Top bugs (Table 10):**
- Control-flow mistakes: 14-48%
- Exception handling: 11-17%
- Resource management/leaks: 7-15%

**Top vulnerabilities (Table 11):**
- Path-traversal & injection: 31-34%
- Hard-coded credentials: 14-30%
- Cryptography misconfiguration: 19-25%

**Implikacja dla QSE:**
- Uzasadnienie dla statycznej analizy strukturalnej niezależnie od Pass@1
- QSE jako Python/DDD analog SonarQube
- Cytować w: Introduction (motivation), Related Work, H2/H5

---

## 2. EvoCodeBench (2602.10171)

**Temat:** Benchmark LLM-driven coding systems z human-performance baseline + self-evolution
**Relevancja:** H3 (feedback poprawia LLM) — trajectory-level evaluation
**Metryki:** Pass@k, TLE, MLE, CE, RTE, Average Runtime, Average Memory
**Dataset:** 3822 problemów, Python/C++/Java/Go/Kotlin

---

## 3. ProxyWar (2602.04296)

**Temat:** Competitive execution-based evaluation przez game arenas
**Relevancja:** QSE komplementarny do dynamic eval — nie zastępuje
**Metryki:** BLEU, CodeBLEU, Pass@k, multi-dim (correctness/efficiency/robustness/adaptability)

---

## 4. AICDBench (2602.02079)

**Temat:** Detekcja AI-generated code — 2M próbek, 77 generatorów, 9 języków
**Relevancja:** Ograniczona — detekcja autorstwa ≠ jakość strukturalna
**Insight:** Słaba generalizacja detektorów pod distribution shift — analogia do layer_violation F1=0.615

---

## 5. Idea First, Code Later (2601.11332)

**Temat:** Rozdzielenie problem-solving od code generation (competitive programming)
**Setup:** 83 ICPC-style problemów, pipeline: Problem → Editorial → Code
**Kluczowy wynik:** Gold editorial daje tylko ~15% poprawy → implementation gap fundamentalny
**Relevancja:** H3 — QSE feedback może zamknąć implementation gap
