from backend.datapilot.catalog import load_catalog
from backend.datapilot.formatting import detect_currency, money, reporting_standard
from backend.datapilot.progress import one_line, parse_answer, step_states
from backend.datapilot.quality import chart_label_audit, evaluate


def states(kinds, **kw):
    return {s.name: s.state for s in step_states(kinds, **kw)}


def test_step_states_follow_the_loop_live():
    assert states(["task"], running=True)["Plan"] == "active"
    assert states(["task", "plan"], running=True)["Code"] == "active"
    assert states(["task", "plan", "code"], running=True)["Run"] == "active"
    s = states(["task", "plan", "code", "exec_error"], running=True)
    assert s["Run"] == "retry" and s["Code"] == "active"           # error loops back to step 03
    assert states(["task", "plan", "code", "exec_ok"], running=True)["Review"] == "active"
    s = states(["task", "plan", "code", "exec_ok", "feedback"], running=True)
    assert s["Review"] == "retry" and s["Code"] == "active"        # feedback loops back to step 03


def test_step_states_after_the_run():
    done = ["task", "plan", "code", "exec_error", "code", "exec_ok", "approved"]
    s = step_states(done, running=False, run_status="approved")
    assert [x.state for x in s] == ["done", "done", "done", "done", "done", "waiting"]
    assert "1 error self-corrected" in s[3].detail
    assert states(done, running=False, run_status="approved", human_verdict="accepted")["Answer"] == "done"
    limit = states(["task", "plan", "code", "exec_ok", "feedback"], running=False, run_status="limit")
    assert limit["Answer"] == "error"


def test_one_line_transcript_matches_spec_shape():
    err = "The script ran, then exited with an error (POSIX exit code: 1)\nIts output was:\nTraceback...\nKeyError: 'revenue'"
    assert one_line("exec_error", err) == "ERROR  KeyError: 'revenue'"
    assert one_line("code", "```python\nprint(1)\n```") == "[writes analysis.py]"
    assert one_line("code", "Fixed. Revenue column is now created before grouping.\n```python\nx\n```").startswith("Fixed.")
    assert one_line("exec_ok", "SAVED: a.png\nSAVED: b.png\nRESULTS\n-----\nElectronics Aug 18.4 L").startswith(
        "OK. Electronics Aug 18.4 L … saved 2 charts")
    assert one_line("approved", "ANSWER ...\nAPPROVED") == "APPROVED"


def test_parse_answer_sections():
    parts = parse_answer("ANSWER\nA.\n\nWHERE IT CAME FROM\nB.\n\nFILES\nx.png | analysis.py\n\nSUGGESTED NEXT QUESTION\nC?")
    assert parts == {"ANSWER": "A.", "WHERE IT CAME FROM": "B.", "FILES": "x.png | analysis.py",
                     "SUGGESTED NEXT QUESTION": "C?"}


def test_chart_label_audit():
    good = "fig, ax = plt.subplots()\nax.set_title('t'); ax.set_xlabel('x'); ax.set_ylabel('y (USD M)')\nfig.savefig('a.png')"
    assert chart_label_audit(good)[:2] == (1, True)
    kw = "ax = df.plot(kind='bar', title='t', xlabel='x', ylabel='y')\nplt.savefig('a.png')"
    assert chart_label_audit(kw)[:2] == (1, True)
    missing = "ax.set_title('t')\nplt.savefig('a.png')\nax.set_title('u'); ax.set_xlabel('x'); ax.set_ylabel('y')\nplt.savefig('b.png')"
    assert chart_label_audit(missing)[:2] == (2, False)


def test_quality_gates(tmp_path):
    script = tmp_path / "analysis.py"
    script.write_text("ax.set_title('t'); ax.set_xlabel('x'); ax.set_ylabel('y')\nplt.savefig('a.png')")
    run = {"status": "approved", "n_messages": 7, "n_exec_errors": 1, "reproducible": 1, "human_verdict": "accepted"}
    gates = evaluate(run, script=script, executor_mode="sandbox", max_messages=12)
    assert [g.status for g in gates] == ["pass"] * 6


def test_formatting_standards():
    assert detect_currency(["order_id", "unit_price_usd"]) == "USD"
    assert detect_currency(["mrr_eur"]) == "EUR"
    assert detect_currency(["units", "discount"]) is None
    assert money(1_840_000, "USD") == "USD 1.84M"
    assert money(1_840_000, "INR", "indian") == "INR 18.4 L"
    assert money(23_000_000, "INR", "indian") == "INR 2.30 Cr"
    assert "ISO 8601" in reporting_standard("EUR", "international")
    assert "lakh" in reporting_standard("INR", "indian")


def test_catalog_files_exist():
    catalog = load_catalog()
    assert len(catalog) >= 5
    for sample in catalog:
        assert sample.path.exists(), sample.file
        assert len(sample.questions) >= 3
