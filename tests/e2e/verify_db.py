#!/usr/bin/env python3
"""
verify_db.py - Helper utility for inspecting Causeway database

Usage:
    verify_db.py --list-traces             Show recent traces
    verify_db.py --list-rules              Show active rules
    verify_db.py --verify-trace TOOL DECISION  Check if trace exists
    verify_db.py --db PATH                 Specify database path
"""

import argparse
import json
import os
import sqlite3
import sys
from pathlib import Path


def get_db_path(custom_path: str | None = None) -> Path:
    """Get database path."""
    if custom_path:
        return Path(custom_path)

    # Look in CAUSEWAY_CWD or current directory
    cwd = Path(os.environ.get('CAUSEWAY_CWD', os.getcwd()))
    return cwd / '.causeway' / 'brain.db'


def list_traces(db_path: Path, limit: int = 10):
    """List recent traces from the database."""
    if not db_path.exists():
        print(f"Database not found: {db_path}")
        return False

    conn = sqlite3.connect(str(db_path))
    conn.row_factory = sqlite3.Row

    cursor = conn.execute("""
        SELECT id, hook_type, tool_name, tool_input, decision, reason,
               matched_rule_ids, duration_ms, timestamp
        FROM traces
        ORDER BY timestamp DESC
        LIMIT ?
    """, (limit,))

    rows = cursor.fetchall()
    conn.close()

    if not rows:
        print("No traces found.")
        return True

    print(f"Recent traces (last {len(rows)}):")
    print("-" * 80)

    for row in rows:
        print(f"ID: {row['id']}")
        print(f"  Timestamp: {row['timestamp']}")
        print(f"  Hook: {row['hook_type']}")
        print(f"  Tool: {row['tool_name']}")
        print(f"  Decision: {row['decision']}")
        print(f"  Duration: {row['duration_ms']}ms")
        print(f"  Matched Rules: {row['matched_rule_ids']}")

        # Truncate tool input for display
        tool_input = row['tool_input'] or ''
        if len(tool_input) > 100:
            tool_input = tool_input[:100] + '...'
        print(f"  Input: {tool_input}")

        # Truncate reason for display
        reason = row['reason'] or ''
        if len(reason) > 200:
            reason = reason[:200] + '...'
        print(f"  Reason: {reason}")
        print()

    return True


def list_rules(db_path: Path, active_only: bool = True):
    """List rules from the database."""
    if not db_path.exists():
        print(f"Database not found: {db_path}")
        return False

    conn = sqlite3.connect(str(db_path))
    conn.row_factory = sqlite3.Row

    query = "SELECT id, type, pattern, description, action, tool, active FROM rules"
    if active_only:
        query += " WHERE active = 1"
    query += " ORDER BY id"

    cursor = conn.execute(query)
    rows = cursor.fetchall()
    conn.close()

    if not rows:
        print("No rules found.")
        return True

    print(f"Rules ({len(rows)} total):")
    print("-" * 80)

    for row in rows:
        status = "active" if row['active'] else "inactive"
        print(f"#{row['id']:3} [{row['action']:5}] [{row['type']:8}] {row['description']}")
        if row['pattern']:
            pattern = row['pattern']
            if len(pattern) > 60:
                pattern = pattern[:60] + '...'
            print(f"      Pattern: {pattern}")
        if row['tool']:
            print(f"      Tool: {row['tool']}")
        print()

    return True


def verify_trace(db_path: Path, tool_name: str, decision: str) -> bool:
    """Verify that a trace exists with the given tool and decision."""
    if not db_path.exists():
        print(f"Database not found: {db_path}")
        return False

    conn = sqlite3.connect(str(db_path))
    conn.row_factory = sqlite3.Row

    cursor = conn.execute("""
        SELECT id, tool_name, decision, reason, timestamp
        FROM traces
        WHERE tool_name = ? AND decision = ?
        ORDER BY timestamp DESC
        LIMIT 1
    """, (tool_name, decision))

    row = cursor.fetchone()
    conn.close()

    if row:
        print(f"Found matching trace:")
        print(f"  ID: {row['id']}")
        print(f"  Tool: {row['tool_name']}")
        print(f"  Decision: {row['decision']}")
        print(f"  Timestamp: {row['timestamp']}")
        return True
    else:
        print(f"No trace found with tool='{tool_name}' and decision='{decision}'")
        return False


def count_traces(db_path: Path, decision: str | None = None) -> int:
    """Count traces, optionally filtered by decision."""
    if not db_path.exists():
        return 0

    conn = sqlite3.connect(str(db_path))

    if decision:
        cursor = conn.execute(
            "SELECT COUNT(*) FROM traces WHERE decision = ?", (decision,)
        )
    else:
        cursor = conn.execute("SELECT COUNT(*) FROM traces")

    count = cursor.fetchone()[0]
    conn.close()
    return count


def main():
    parser = argparse.ArgumentParser(
        description='Inspect Causeway database',
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog="""
Examples:
    verify_db.py --list-traces
    verify_db.py --list-rules
    verify_db.py --verify-trace Bash block
    verify_db.py --db /path/to/brain.db --list-traces
        """
    )

    parser.add_argument('--db', help='Path to database file')
    parser.add_argument('--list-traces', action='store_true', help='List recent traces')
    parser.add_argument('--list-rules', action='store_true', help='List active rules')
    parser.add_argument('--verify-trace', nargs=2, metavar=('TOOL', 'DECISION'),
                        help='Verify trace exists with given tool and decision')
    parser.add_argument('--count-traces', action='store_true', help='Count all traces')
    parser.add_argument('--count-by-decision', metavar='DECISION',
                        help='Count traces with specific decision')
    parser.add_argument('--limit', type=int, default=10, help='Limit for list operations')

    args = parser.parse_args()

    db_path = get_db_path(args.db)

    if args.list_traces:
        success = list_traces(db_path, args.limit)
        sys.exit(0 if success else 1)

    if args.list_rules:
        success = list_rules(db_path)
        sys.exit(0 if success else 1)

    if args.verify_trace:
        tool_name, decision = args.verify_trace
        success = verify_trace(db_path, tool_name, decision)
        sys.exit(0 if success else 1)

    if args.count_traces:
        count = count_traces(db_path)
        print(f"Total traces: {count}")
        sys.exit(0)

    if args.count_by_decision:
        count = count_traces(db_path, args.count_by_decision)
        print(f"Traces with decision '{args.count_by_decision}': {count}")
        sys.exit(0)

    # Default: show help
    parser.print_help()
    sys.exit(0)


if __name__ == '__main__':
    main()
