"""Shared database utilities."""
import os
import sqlite3
import sqlite_vec
import numpy as np
from pathlib import Path


def get_db_path() -> Path:
    """Get database path - project-local .causeway/brain.db or env override."""
    if env_path := os.environ.get("CAUSEWAY_DB"):
        return Path(env_path)

    # Look for .causeway/ in current directory or parents
    # CAUSEWAY_CWD is set by CLI when it changes to package dir for uv
    cwd = Path(os.environ.get("CAUSEWAY_CWD", os.getcwd()))
    for parent in [cwd] + list(cwd.parents):
        candidate = parent / ".causeway" / "brain.db"
        if candidate.exists():
            return candidate
        # Stop at home directory
        if parent == Path.home():
            break

    # Default: .causeway/ in current working directory
    return cwd / ".causeway" / "brain.db"


# For backwards compatibility
DB_PATH = get_db_path()


def get_connection(db_path: Path | None = None) -> sqlite3.Connection:
    """Get database connection with vec extension loaded."""
    path = db_path or get_db_path()
    conn = sqlite3.connect(str(path))
    conn.enable_load_extension(True)
    sqlite_vec.load(conn)
    conn.enable_load_extension(False)
    conn.row_factory = sqlite3.Row
    return conn


def serialize_vector(vec: list[float]) -> bytes:
    """Serialize vector for storage."""
    return np.array(vec, dtype=np.float32).tobytes()


def init_db(db_path: Path | None = None):
    """Initialize database with base schema."""
    path = db_path or get_db_path()
    # Create .causeway/ directory if needed
    path.parent.mkdir(parents=True, exist_ok=True)
    conn = get_connection(path)

    # Core tables (legacy-compatible rules table first)
    conn.executescript("""
        -- Schema migrations tracking
        CREATE TABLE IF NOT EXISTS migrations (
            id INTEGER PRIMARY KEY,
            name TEXT NOT NULL UNIQUE,
            applied_at DATETIME DEFAULT CURRENT_TIMESTAMP
        );

        -- Rules for pre-flight checks (base schema, columns added via migration)
        CREATE TABLE IF NOT EXISTS rules (
            id INTEGER PRIMARY KEY,
            type TEXT DEFAULT 'regex',
            pattern TEXT,
            description TEXT NOT NULL,
            tool TEXT,
            action TEXT DEFAULT 'block',
            active INTEGER DEFAULT 1,
            priority INTEGER DEFAULT 0,
            created_at DATETIME DEFAULT CURRENT_TIMESTAMP
        );

        -- Vector embeddings for semantic rule matching
        CREATE VIRTUAL TABLE IF NOT EXISTS rule_embeddings USING vec0(
            rule_id INTEGER PRIMARY KEY,
            embedding FLOAT[384]
        );
    """)

    # Settings table
    conn.execute("""
        CREATE TABLE IF NOT EXISTS settings (
            key TEXT PRIMARY KEY,
            value TEXT NOT NULL
        )
    """)

    # New tables (v2 schema)
    conn.executescript("""
        -- Rule sets: groups of rules assignable to projects
        CREATE TABLE IF NOT EXISTS rule_sets (
            id INTEGER PRIMARY KEY,
            name TEXT NOT NULL UNIQUE,
            description TEXT,
            created_at DATETIME DEFAULT CURRENT_TIMESTAMP
        );

        -- Projects: codebases/folders where Claude Code runs
        CREATE TABLE IF NOT EXISTS projects (
            id INTEGER PRIMARY KEY,
            path TEXT NOT NULL UNIQUE,
            name TEXT,
            rule_set_id INTEGER,
            created_at DATETIME DEFAULT CURRENT_TIMESTAMP,
            FOREIGN KEY (rule_set_id) REFERENCES rule_sets(id)
        );

        -- Sessions: Claude Code conversations
        CREATE TABLE IF NOT EXISTS sessions (
            id INTEGER PRIMARY KEY,
            project_id INTEGER NOT NULL,
            external_id TEXT UNIQUE,
            transcript_path TEXT,
            task TEXT,
            started_at DATETIME DEFAULT CURRENT_TIMESTAMP,
            ended_at DATETIME,
            status TEXT DEFAULT 'active',
            FOREIGN KEY (project_id) REFERENCES projects(id)
        );

        -- Messages: individual turns in a session
        CREATE TABLE IF NOT EXISTS messages (
            id INTEGER PRIMARY KEY,
            session_id INTEGER NOT NULL,
            external_id TEXT,
            role TEXT NOT NULL,
            content TEXT,
            timestamp DATETIME DEFAULT CURRENT_TIMESTAMP,
            FOREIGN KEY (session_id) REFERENCES sessions(id)
        );

        -- Tool calls: tool invocations within messages
        CREATE TABLE IF NOT EXISTS tool_calls (
            id INTEGER PRIMARY KEY,
            message_id INTEGER NOT NULL,
            tool TEXT NOT NULL,
            input TEXT,
            output TEXT,
            success INTEGER DEFAULT 1,
            error_message TEXT,
            blocked_by_rule_id INTEGER,
            duration_ms INTEGER,
            timestamp DATETIME DEFAULT CURRENT_TIMESTAMP,
            FOREIGN KEY (message_id) REFERENCES messages(id),
            FOREIGN KEY (blocked_by_rule_id) REFERENCES rules(id)
        );

        -- Rule triggers: when a rule matched a tool call
        CREATE TABLE IF NOT EXISTS rule_triggers (
            id INTEGER PRIMARY KEY,
            rule_id INTEGER NOT NULL,
            tool_call_id INTEGER NOT NULL,
            action_taken TEXT NOT NULL,
            llm_reasoning TEXT,
            timestamp DATETIME DEFAULT CURRENT_TIMESTAMP,
            FOREIGN KEY (rule_id) REFERENCES rules(id),
            FOREIGN KEY (tool_call_id) REFERENCES tool_calls(id)
        );

        -- Hook execution traces for debugging
        CREATE TABLE IF NOT EXISTS traces (
            id INTEGER PRIMARY KEY,
            hook_type TEXT NOT NULL,  -- 'pre' or 'stop'
            tool_name TEXT,
            tool_input TEXT,
            rules_checked INTEGER DEFAULT 0,
            rules_matched INTEGER DEFAULT 0,
            matched_rule_ids TEXT,  -- JSON array of matched rule IDs
            decision TEXT,  -- 'allow', 'block', 'warn'
            reason TEXT,
            llm_prompt TEXT,  -- prompt sent to LLM (if any)
            llm_response TEXT,  -- response from LLM (if any)
            duration_ms INTEGER,
            timestamp DATETIME DEFAULT CURRENT_TIMESTAMP
        );

        -- Indexes for performance
        CREATE INDEX IF NOT EXISTS idx_messages_session ON messages(session_id);
        CREATE INDEX IF NOT EXISTS idx_tool_calls_message ON tool_calls(message_id);
        CREATE INDEX IF NOT EXISTS idx_rule_triggers_tool_call ON rule_triggers(tool_call_id);
        CREATE INDEX IF NOT EXISTS idx_sessions_project ON sessions(project_id);
        CREATE INDEX IF NOT EXISTS idx_traces_timestamp ON traces(timestamp);
    """)
    conn.commit()

    # Run migrations (adds columns to existing tables)
    _run_migrations(conn)
    conn.close()
    return path


def _run_migrations(conn):
    """Run pending migrations."""
    # Check existing columns in rules table
    cursor = conn.execute("PRAGMA table_info(rules)")
    columns = {row[1] for row in cursor.fetchall()}

    # Add columns if missing
    if 'problem' not in columns:
        conn.execute("ALTER TABLE rules ADD COLUMN problem TEXT")
    if 'solution' not in columns:
        conn.execute("ALTER TABLE rules ADD COLUMN solution TEXT")
    if 'rule_set_id' not in columns:
        conn.execute("ALTER TABLE rules ADD COLUMN rule_set_id INTEGER REFERENCES rule_sets(id)")
    if 'source_message_id' not in columns:
        conn.execute("ALTER TABLE rules ADD COLUMN source_message_id INTEGER REFERENCES messages(id)")
    if 'source_session_id' not in columns:
        conn.execute("ALTER TABLE rules ADD COLUMN source_session_id INTEGER REFERENCES sessions(id)")

    # Display fields (v3)
    if 'color' not in columns:
        conn.execute("ALTER TABLE rules ADD COLUMN color TEXT")  # hex color for UI display
    if 'metadata' not in columns:
        conn.execute("ALTER TABLE rules ADD COLUMN metadata TEXT")  # JSON object for extra data

    # Scope fields (v3) - simplified: patterns array + LLM review flag
    if 'patterns' not in columns:
        conn.execute("ALTER TABLE rules ADD COLUMN patterns TEXT")  # JSON array of regex patterns
    if 'llm_review' not in columns:
        conn.execute("ALTER TABLE rules ADD COLUMN llm_review INTEGER DEFAULT 0")  # 0=direct action, 1=LLM decides
    if 'prompt' not in columns:
        conn.execute("ALTER TABLE rules ADD COLUMN prompt TEXT")  # context/guidance for LLM review
    if 'hard' not in columns:
        conn.execute("ALTER TABLE rules ADD COLUMN hard INTEGER DEFAULT 0")  # 1=cannot be overridden by LLM

    # Create default rule set if none exists
    existing = conn.execute("SELECT id FROM rule_sets WHERE name = 'default'").fetchone()
    if not existing:
        conn.execute("INSERT INTO rule_sets (name, description) VALUES ('default', 'Default rule set')")

    conn.commit()


if __name__ == "__main__":
    path = init_db()
    print(f"Database initialized at {path}")
