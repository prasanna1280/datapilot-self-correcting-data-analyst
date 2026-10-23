# Testing

## Automated (no API key, ~20 s)
```bash
python -m pytest
```
| File | Covers |
|---|---|
| `test_selector.py` | Routing: error → Coder, ok → Reviewer, feedback → Coder, follow-up → Planner |
| `test_team_replay.py` | Full team with a scripted model + **real code execution**: KeyError → fix → APPROVED, DB persistence, reproducibility, PDF, follow-up resumes state, 12-message limit |
| `test_sandbox.py` | Sandbox runs in session folder, hides secrets, rejects path traversal, enforces timeout |
| `test_safety.py` | Static gate allows normal analysis code and blocks dangerous code |
| `test_data_loader.py` | CSV profile, multi-sheet Excel (stacked / single sheet), errors |

## Smoke test (any environment)
```bash
python scripts/smoke_test.py                              # local executor, scripted model
docker compose exec app python scripts/smoke_test.py      # sandbox container, scripted model
docker compose exec app python scripts/smoke_test.py --live   # real OpenAI run (costs a few cents)
```

## Manual UI checklist
1. Open the app → **Use sample** → **Ask the sample question**.
2. Watch the trail: Planner → Coder → Executor (OK/ERROR) → … → Reviewer **APPROVED**.
3. Check the answer card, two charts with titles/axis labels/units, and the downloads (`analysis.py`, PNGs, PDF).
4. **Reproducibility check** → "Same numbers ✔".
5. Click **Approve answer**, then ask a follow-up: *"Did discounts on Earbuds X2 change between August and September?"*. It continues in the same session.
6. Upload `data/sample/sales_2026.xlsx` → choose "All 4 sheets (stacked)".
