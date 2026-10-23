import pytest

from backend.sandbox import server

SID = "ab" * 16


@pytest.fixture
def workspace(tmp_path, monkeypatch):
    monkeypatch.setattr(server, "WORKSPACE", tmp_path.resolve())
    (tmp_path / SID).mkdir()
    return tmp_path


def test_runs_code_in_session_folder(workspace):
    res = server.run_code(SID, "analysis.py", "open('out.txt','w').write('hi'); print(6*7)", 10)
    assert res == {"exit_code": 0, "output": "42\n"}
    assert (workspace / SID / "out.txt").read_text() == "hi"
    assert (workspace / SID / "analysis.py").exists()


def test_errors_are_returned_not_raised(workspace):
    res = server.run_code(SID, "analysis.py", "raise KeyError('revenue')", 10)
    assert res["exit_code"] == 1 and "KeyError: 'revenue'" in res["output"]


def test_secrets_are_not_visible(workspace, monkeypatch):
    monkeypatch.setenv("OPENAI_API_KEY", "sk-secret")
    res = server.run_code(SID, "analysis.py", "import os; print(os.environ.get('OPENAI_API_KEY'))", 10)
    assert res["output"].strip() == "None"


@pytest.mark.parametrize("sid,fname", [("../etc", "a.py"), (SID, "../x.py"), (SID, "a.sh"), ("cd" * 16, "a.py")])
def test_rejects_bad_paths(workspace, sid, fname):
    assert server.run_code(sid, fname, "print(1)", 5)["exit_code"] == 1


def test_timeout(workspace):
    res = server.run_code(SID, "slow.py", "import time; time.sleep(5)", 1)
    assert res["exit_code"] == 124 and "Timeout" in res["output"]
