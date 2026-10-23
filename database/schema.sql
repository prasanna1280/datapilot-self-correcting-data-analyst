-- DataPilot SQLite schema. Applied automatically by database/db.py (idempotent).

CREATE TABLE IF NOT EXISTS sessions (
    id            TEXT PRIMARY KEY,              -- uuid4 hex, also the sandbox folder name
    created_at    TEXT NOT NULL DEFAULT (datetime('now')),
    dataset_name  TEXT NOT NULL,
    dataset_rows  INTEGER,
    data_profile  TEXT,                           -- column summary given to the Planner
    dataset_cols  INTEGER,
    sample_id     TEXT,                           -- catalog id when a sample dataset was used
    currency      TEXT DEFAULT 'USD',             -- ISO 4217
    number_style  TEXT DEFAULT 'international',   -- international (K/M/B) | indian (L/Cr)
    team_state    TEXT                            -- AutoGen team.save_state() JSON (for follow-ups)
);

CREATE TABLE IF NOT EXISTS runs (
    id            INTEGER PRIMARY KEY AUTOINCREMENT,
    session_id    TEXT NOT NULL REFERENCES sessions(id) ON DELETE CASCADE,
    run_no        INTEGER NOT NULL,               -- 1 = first question, 2+ = follow-ups
    question      TEXT NOT NULL,
    started_at    TEXT NOT NULL DEFAULT (datetime('now')),
    finished_at   TEXT,
    stop_reason   TEXT,
    status        TEXT NOT NULL DEFAULT 'running', -- running | approved | limit | error
    answer        TEXT,                           -- Reviewer's final answer
    n_messages    INTEGER DEFAULT 0,
    n_exec_errors INTEGER DEFAULT 0,              -- how many times the Coder had to self-correct
    n_feedback    INTEGER DEFAULT 0,              -- Reviewer send-backs
    reproducible  INTEGER,                        -- NULL = not checked, 1 = same output, 0 = differs
    model         TEXT,
    duration_s    REAL,
    human_verdict TEXT,                           -- NULL | accepted | rejected | follow_up
    UNIQUE (session_id, run_no)
);

CREATE TABLE IF NOT EXISTS messages (
    id          INTEGER PRIMARY KEY AUTOINCREMENT,
    session_id  TEXT NOT NULL REFERENCES sessions(id) ON DELETE CASCADE,
    run_no      INTEGER NOT NULL,
    seq         INTEGER NOT NULL,
    source      TEXT NOT NULL,                    -- user | Planner | Coder | Executor | Reviewer
    kind        TEXT NOT NULL,                    -- task | plan | code | exec_ok | exec_error | feedback | approved | other
    content     TEXT NOT NULL,
    elapsed_s   REAL,                             -- seconds since the run started
    created_at  TEXT NOT NULL DEFAULT (datetime('now'))
);

CREATE INDEX IF NOT EXISTS idx_messages_session ON messages (session_id, run_no, seq);
CREATE INDEX IF NOT EXISTS idx_runs_session ON runs (session_id, run_no);
