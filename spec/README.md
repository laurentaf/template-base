# SDD Workflow — Spec-Driven Development

Every feature follows a phased workflow with mandatory quality gates.
Phases must be completed in order. No phase can start without the previous phase's output.

## Phase Overview

```
Phase 0: BRAINSTORM  →  Phase 1: DEFINE  →  Phase 2: DESIGN  →  Phase 3: BUILD  →  Phase 4: SHIP
  Explore ideas         Scope & contract    Architecture        Implement           Archive & report
```

## Phase Details

### Phase 0 — Brainstorm
**Input:** User request or idea
**Output:** `spec/brainstorm/{feature}/BRAINSTORM.md`
**Quality gate (must pass before Phase 1):**
- [ ] At least 3 approaches compared
- [ ] At least 3 questions answered about the problem
- [ ] YAGNI filter applied (what's explicitly out of scope)
- [ ] Success criteria defined

### Phase 1 — Define
**Input:** BRAINSTORM document
**Output:** `spec/define/{feature}/DEFINE.md`
**Quality gate (must pass before Phase 2):**
- [ ] Clarity score >= 12/15 (5 criteria scored 1-3)
- [ ] Requirements signed off
- [ ] Acceptance criteria defined
- [ ] All ambiguous terms clarified

**Clarity scoring:**
| Criterion | 1 (Weak) | 2 (Adequate) | 3 (Strong) |
|-----------|----------|--------------|------------|
| Problem scope | Vague | Bounded | Precise boundaries |
| Success metric | Missing | Defined | Quantified |
| Stakeholders | Unknown | Listed | Contacted |
| Constraints | Assumed | Documented | Verified |
| Dependencies | Hidden | Listed | Mapped |

### Phase 2 — Design
**Input:** DEFINE document
**Output:** `spec/design/{feature}/DESIGN.md`
**Quality gate (must pass before Phase 3):**
- [ ] Complete file manifest (every file to be created)
- [ ] Architecture Decision Records (ADRs) for key choices
- [ ] Schema design for all data entities
- [ ] Agent assignments per file (`@{agent-name}`)
- [ ] Data flow diagram (source → process → sink)

### Phase 3 — Build
**Input:** DESIGN document
**Output:** Code in `src/` + `spec/build/{feature}/BUILD_REPORT.md`
**Quality gate (must pass before Phase 4):**
- [ ] All files in manifest exist
- [ ] All tests pass (`uv run pytest`)
- [ ] Ruff formatting clean (`uv run ruff check .`)
- [ ] No hardcoded secrets
- [ ] Observability wired in (Phoenix traces)

### Phase 4 — Ship
**Input:** BUILD_REPORT + passing tests
**Output:** `spec/archive/{feature}/SHIPPED.md`
**Quality gate:**
- [ ] Validation report exists (score >= 90)
- [ ] Lessons captured in `spec/lessons.md`
- [ ] Knowledge base updated if applicable
- [ ] GitHub pushed / PR created

### Cross-phase: Iterate
**Trigger:** Requirements change or bug found
**Action:** Update the relevant phase document
**Cascade:** Check downstream documents for staleness and flag them

## Validation Scoring (Phase 3.5)

Before shipping, run validation:

```powershell
uv run python spec/quality_gates.py validate --feature my-feature
```

Scoring weights:
- Spec completeness: 30%
- Code quality: 25%
- Test coverage: 25%
- Security review: 20%

**Pass: score >= 90 AND 0 CRITICAL findings**
**Fail: score < 90 OR any CRITICAL finding → ROADMAP of required fixes**
