# Demo Cheat Sheet — L3 HIL Verification

## Setup (do this before joining the call)
- [ ] Open the repo tab and have `requirements/sources/REQ-SYS-AEB-002.yaml` visible — this is the compound requirement Devin will decompose
- [ ] Open a second Browser tab on `http://localhost:5001/` (the V&V pipeline dashboard, visible via Devin's Browser tab once the session starts)

## Demo Flow
1. Walk the audience through the three requirement formats — YAML (Jama-style), `.feature` (Gherkin), and `.xlsx` (spreadsheet). Highlight that `REQ-SYS-AEB-002` is compound: it bundles deceleration, warning lamp, haptic alert, and ramp-to-full-braking into one statement. *This is what V&V engineers deal with daily.*
2. Trigger Devin: in a fresh session against this repo, prompt **"Analyze and process REQ-SYS-AEB-002 end-to-end — decompose it, map through the bench-boundary abstraction for bench_beta, generate test artifacts, execute against the replay harness, and produce a traceability report as a PR."**
3. Narrate the dashboard stages turning green: requirement analysis finds the compound, decomposition produces atomic Gherkin scenarios, abstraction mapping routes signals through the partial bench, test scripts are generated without hard-coded CAN IDs. *The key talking point: abstract steps like "set ignition on" map to concrete signals through the OEM's own abstraction library — Devin doesn't invent CAN IDs.*
4. When execution completes, switch to the PR — show the generated `.feature` files in `scenarios/generated/`, the test scripts in `test_artifacts/generated/`, and the traceability report linking every result back to the original compound requirement.
5. Close with the traceability matrix on the dashboard — every scenario traces back to `REQ-SYS-AEB-002`, decomposed scenarios are tagged, and the test engineer can approve or iterate. *This is the review loop that keeps engineers in control.*
