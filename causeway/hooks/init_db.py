#!/usr/bin/env python3
"""SessionStart hook: Initialize per-folder database if missing."""
import os
import sys
from pathlib import Path


def main():
    """Initialize .causeway/brain.db in current directory if it doesn't exist."""
    cwd = Path(os.environ.get("CAUSEWAY_CWD", os.getcwd()))
    db_path = cwd / ".causeway" / "brain.db"

    if db_path.exists():
        return  # Already initialized

    # Import and init (this loads dependencies)
    causeway_dir = Path(__file__).parent.parent
    sys.path.insert(0, str(causeway_dir))

    from db import init_db
    init_db(db_path)


if __name__ == "__main__":
    main()
