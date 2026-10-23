🚀 Built DataPilot: a self-correcting AI data analyst

Ask a business question in plain English and get back a reviewed answer with charts. You don't write any code yourself.

How it works: a team of AutoGen agents works through 6 steps.
1️⃣ Ask: upload a CSV or Excel file and ask your question
2️⃣ Plan: the Planner breaks the question into steps
3️⃣ Code: the Coder writes a Python analysis (pandas + matplotlib)
4️⃣ Run: the Executor runs it in an isolated Docker sandbox
5️⃣ Review: the Reviewer checks the numbers, the logic and the chart labels
6️⃣ Answer: a human approves the answer, then can ask a follow-up

🔁 What makes it different: if the code fails, or the Reviewer pushes back, the work goes back to the Coder automatically and gets fixed. In one live run on a 3-sheet HR workbook, the agents hit a matplotlib error, fixed it themselves, and still returned the right answer.

🛡️ Guardrails
• Stops on APPROVED or after 12 messages
• AI-written code runs in a sandbox with no API keys, no internet and a read-only file system
• A safety check scans the code before it runs
• After approval, analysis.py is run again to prove the numbers come out the same

📦 What you get: the answer and where the numbers came from, labelled charts, a re-runnable analysis.py and a one-page PDF report. Dates and currencies follow international formats (ISO dates, ISO currency codes, K/M/B or lakh/crore).

📊 Five sample datasets are built in: retail (INR), global e-commerce (USD), SaaS subscriptions (EUR), supply chain (USD) and HR (Excel). The agents answered all five correctly with GPT-4.1.

🧰 Built with AutoGen 0.7 (SelectorGroupChat) · GPT-4.1 · Streamlit · pandas · SQLite · Docker · Traefik + HTTPS on a Hostinger VPS

🌐 Live app: https://datapilot.prasanna.digital
🔐 The app is password-protected to keep the OpenAI costs in check. DM me for the login password if you'd like to explore it.
💻 Code: https://github.com/prasanna1280/datapilot-self-correcting-data-analyst

#AgenticAI #AutoGen #MultiAgentSystems #GenerativeAI #DataAnalytics #Python #Streamlit #OpenAI #Docker #LLM
