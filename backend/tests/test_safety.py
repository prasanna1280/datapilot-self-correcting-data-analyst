import pytest
from autogen_agentchat.agents import ApprovalRequest

from backend.datapilot.safety import approve_code, check_code

SAFE = '''# filename: analysis.py
import matplotlib
matplotlib.use("Agg")
import matplotlib.pyplot as plt
import pandas as pd
df = pd.read_csv("data.csv")
df["month"] = pd.to_datetime(df["order_date"]).dt.strftime("%Y/%m")
plt.title("Revenue / month"); plt.savefig("chart.png")
'''


def test_normal_analysis_code_passes():
    assert check_code(SAFE) is None
    assert approve_code(ApprovalRequest(code=f"```python\n{SAFE}\n```", context=[])).approved


@pytest.mark.parametrize("code,why", [
    ("import subprocess; subprocess.run(['ls'])", "subprocess"),
    ("import os; print(os.environ)", "'os'"),
    ("import requests", "requests"),
    ("from urllib import request", "urllib"),
    ("exec('print(1)')", "exec"),
    ("import pandas as pd; pd.read_csv('/etc/passwd')", "outside"),
    ("import pandas as pd; pd.read_csv('../other/data.csv')", "outside"),
    ("import pandas as pd; pd.read_pickle('x.pkl')", "read_pickle"),
])
def test_dangerous_code_is_rejected(code, why):
    reason = check_code(code)
    assert reason and why in reason


def test_syntax_errors_are_left_for_the_executor():
    assert check_code("def broken(:") is None
