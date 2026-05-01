# Implementation Plan — L3 HIL Verification Demo

> Committed before the rest of the scaffold per the Demo Scaffold playbook (Step 2b).

## 1. What the demo proves

Devin can take a **system-level (L3) requirement** — written in natural language,
exported from a requirements management tool, pulled from a spreadsheet row, or
already expressed as Gherkin — and perform end-to-end V&V work: assess whether
the requirement is atomic, testable, and unambiguous; decompose compound
requirements into multiple atomic Gherkin scenarios while preserving traceability;
map abstract test steps ("set ignition on", "accelerate to 60 kph") through an
OEM's abstraction and bench-boundary libraries into concrete HIL signals; generate
executable test artifacts; run them against the bench; and produce a traceability
report linking every result back to the original requirement. Test engineers stay
in the loop via PR review.

## 2. What Devin does live (one sentence)

Ingest a system-level AEB requirement, decompose it into atomic Gherkin scenarios,
map abstract steps through the bench-boundary abstraction library, generate and
execute test scripts against the mock HIL bench, and open a PR with the generated
scenarios, test artifacts, execution results, and a traceability report.

## 3. Stack and rationale

| Layer | Choice | Why | Source |
|---|---|---|---|
| Domain | Automatic Emergency Braking (AEB) | System-level feature spanning multiple ECUs (ADAS controller, brake ECU, radar, camera, instrument cluster); well-understood by OEM audiences; clear L3 V&V scope | Euro NCAP AEB test protocol v4.1; ISO 22839 (Forward vehicle collision mitigation) |
| Requirements format | YAML (Jama-style export), `.feature` (Gherkin), `.xlsx` (spreadsheet) | Covers the three ingestion paths the customer described: tool exports, feature-engineer-authored Gherkin, and spreadsheet rows | Cucumber Gherkin Reference; Jama Connect REST API export schema |
| Scenario language | Gherkin (`.feature` files) | Industry-standard BDD specification language; readable by both engineers and test automation tooling; the customer's target methodology treats requirements as executable specifications | Cucumber docs — cucumber.io/docs/gherkin/reference |
| Abstraction layer | YAML action library + bench-boundary config + signal dictionary | Maps abstract actions (e.g. "set ignition on") → concrete bench operations (e.g. write CAN signal `IgnitionStatus` on `0x130`). Modeled on the ASAM XIL Framework's MAPort variable mapping pattern | ASAM XIL 3.0 spec — Framework section on abstract-to-concrete identifier mapping |
| Bench boundary | JSON config per bench | Defines which ECUs are physical vs simulated on each bench; determines signal routing and stub behavior. Realistic for partial-ECU bench configurations at OEMs | Common HIL bench engineering practice; dSPACE ConfigurationDesk bench topology concept |
| Test artifact format | Python test scripts (ECU-TEST style) | TraceTronic ECU-TEST uses Python-based test procedures with signal access APIs. Generated scripts use abstract runner interface, not hard-coded CAN IDs | TraceTronic ecu.test product docs — Python extensibility |
| Mock HIL runner | Python replay harness with pre-captured JSON traces | Real HIL hardware (dSPACE SCALEXIO, NI VeriStand) is unreachable from a Devin VM; replay harness produces identical DataFrame output so downstream analysis is bench-agnostic | Same pattern as `tedfoley-cog/chassis-hil-demo` runners |
| Dashboard | FastAPI + Jinja2, port 5001 | Lightweight V&V pipeline visualization showing requirement → scenario → test → result flow with traceability matrix | FastAPI docs |
| CI | GitHub Actions: install deps, lint, typecheck, test | Produces green check; same shape as other `tedfoley-cog` demo repos | GitHub Actions docs |

## 4. Repo layout

```
README.md
DEMO_NOTES.md
.gitignore
.github/workflows/ci.yml
pyproject.toml

docs/
  IMPLEMENTATION_PLAN.md          # This file
  flowchart.html                  # Pipeline flowchart (Mermaid, standalone)
  flowchart.png                   # Rendered PNG for README

requirements/
  sources/
    REQ-SYS-AEB-001.yaml          # Atomic requirement: AEB activation timing
    REQ-SYS-AEB-002.yaml          # Compound requirement: AEB deceleration + warning (needs decomposition)
    REQ-SYS-AEB-003.feature       # Already in Gherkin: FCW display timing
    requirements_matrix.xlsx      # Spreadsheet import format (openpyxl-readable)

scenarios/
  existing/
    aeb_basic_stop.feature        # Pre-existing Gherkin (shows "update affected tests" workflow)
  generated/
    .gitkeep                      # Devin fills this live

abstraction/
  action_library.yaml             # Abstract actions → signal-level operations
  bench_boundary.yaml             # ECU topology: physical vs simulated per bench
  signal_dictionary.yaml          # Signal name → CAN address + scaling + unit

bench_configs/
  bench_alpha.json                # Full bench: all ECUs physical
  bench_beta.json                 # Partial bench: brake + ADAS physical, radar simulated

harness/
  __init__.py
  models.py                       # Shared data models (Requirement, Scenario, TestArtifact, etc.)
  analyzer.py                     # Requirement quality assessment (atomic? testable? unambiguous?)
  decomposer.py                   # Compound requirement → atomic Gherkin scenarios
  mapper.py                       # Abstract Gherkin steps → concrete bench signals via abstraction lib
  generator.py                    # Gherkin scenario + signal mapping → executable test script
  executor.py                     # Mock HIL test executor (replays pre-captured traces)
  tracer.py                       # Traceability matrix: requirement → scenario → test → result

traces/
  aeb_40kph_stationary.json       # Pre-captured trace: 40 kph approach to stationary target
  aeb_60kph_braking.json          # Pre-captured trace: 60 kph approach to braking target

dashboard/
  app.py                          # FastAPI V&V dashboard
  templates/
    index.html                    # Pipeline visualization with traceability matrix
  state.json                      # Current pipeline state

test_artifacts/
  templates/
    test_template.py.j2           # Jinja2 template for ECU-TEST style test scripts
  generated/
    .gitkeep                      # Devin fills this live

tests/
  conftest.py
  test_analyzer.py                # Unit tests for requirement quality assessment
  test_decomposer.py              # Unit tests for Gherkin decomposition
  test_mapper.py                  # Unit tests for abstraction mapping
```

~25 source files. Initial state only — `scenarios/generated/` and `test_artifacts/generated/`
are empty; Devin fills them during the live demo.

## 5. Flowchart outline

Nodes and edges for the demo-flow diagram:

1. **Requirement Source** (Jama YAML / Gherkin `.feature` / Spreadsheet `.xlsx`)
2. **Devin Session Triggered** (prompt or playbook macro)
3. **Requirement Analysis** — assess atomicity, testability, ambiguity
4. **Decision: Atomic?**
   - Yes → proceed to mapping
   - No → **Decompose** into atomic Gherkin scenarios (with traceability)
5. **Abstraction Mapping** — map abstract steps through action library + bench boundary
6. **Test Artifact Generation** — produce ECU-TEST style Python test scripts
7. **Test Execution** — run against mock HIL bench (replay harness)
8. **Impact Analysis** — check existing tests affected by requirement changes
9. **Traceability Report** — requirement → scenario → test → result matrix
10. **PR with all artifacts** — scenarios, test scripts, results, traceability
11. **Engineer Reviews** — test engineer approves or requests changes
12. **Decision: Approved?** → Ready for bench execution / iterate

## 6. Runtime plan

"Appears runnable" via mock HIL replay harness. Real dSPACE/NI HIL hardware is
unreachable from a Devin VM, so the executor replays pre-captured JSON trace
files. The replay produces the same signal DataFrame that a real bench would,
so downstream analysis (pass/fail evaluation, traceability reporting, dashboard
visualization) is identical. Called out in the PR description and README.

Commands:
- `uv sync` — install all dependencies
- `uv run python -m harness.analyzer requirements/sources/REQ-SYS-AEB-002.yaml` — analyze a requirement
- `uv run python -m harness.executor` — run all generated tests against replay harness
- `uv run uvicorn dashboard.app:app --port 5001` — launch V&V dashboard
- `uv run pytest` — run unit tests

## 7. CI plan

Single workflow: checkout → install uv → `uv sync` → `uv run ruff check .` →
`uv run mypy harness/ tests/` → `uv run pytest -q`. Under 40 lines of YAML.

## 8. Risks and unknowns

- **ECU-TEST proprietary API**: TraceTronic's ecu.test API is not publicly documented
  in full. Generated test artifacts use a generic Python runner interface modeled on
  the ASAM XIL MAPort pattern rather than the exact ecu.test API. Called out in the
  README. If the customer has specific ecu.test workspace examples, those could be
  wired in as a second demo scene.
- **Jama export schema**: Jama Connect's REST API export is proprietary; the YAML
  format used here is a simplified representation. Real integration would use
  Jama's REST API or ReqIF XML export.
- **Bench-boundary complexity**: Real OEM bench configs are far more complex (hundreds
  of signals, FMU co-simulation, timing constraints). The demo uses a representative
  subset (~15 signals) to keep the demo crisp.
- **Spreadsheet format**: The `.xlsx` requirement matrix uses a simplified schema.
  Real customers may have highly customized Excel templates — the demo shows the
  concept; exact column mapping would be configured per engagement.
