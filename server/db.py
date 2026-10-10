import sqlite3
import json
from pathlib import Path
from typing import List, Dict, Any
from guardrails import validate_and_format_query, SQLSecurityError
from audit import log_query

# Anchor the DB path relative to this file: safe-text-to-sql-mcp/data/chinook.db
BASE_DIR = Path(__file__).resolve().parent.parent
DB_PATH = BASE_DIR / "data" / "chinook.db"

ALLOWED_TABLES = {
    "Album", "Artist", "Customer", "Genre", 
    "Invoice", "InvoiceLine", "MediaType", "Track"
}

def get_connection():
    if not DB_PATH.exists():
        raise FileNotFoundError(f"Database not found at expected path: {DB_PATH}")
    conn = sqlite3.connect(str(DB_PATH), check_same_thread=False)
    conn.row_factory = sqlite3.Row
    return conn

def list_allowed_tables() -> List[str]:
    """Returns a list of tables the LLM is permitted to query."""
    return sorted(list(ALLOWED_TABLES))

def get_table_schema(table_name: str) -> str:
    """Returns the CREATE TABLE statement for a given allowed table."""
    if table_name not in ALLOWED_TABLES:
        return f"Error: Table '{table_name}' is not allowed or does not exist."
    
    conn = get_connection()
    cursor = conn.cursor()
    cursor.execute(
        "SELECT sql FROM sqlite_master WHERE type='table' AND name=?", 
        (table_name,)
    )
    result = cursor.fetchone()
    conn.close()
    
    if result:
        return result["sql"]
    return f"Error: Schema for '{table_name}' not found."

def execute_read_query(query: str) -> str:
    """Validates and executes a SQL query, returning the results as JSON."""
    try:
        # Run through AST validation layer
        sanitized_sql = validate_and_format_query(query)
    except SQLSecurityError as e:
        return json.dumps({"error": "SecurityViolation", "details": str(e)}, indent=2)

    conn = get_connection()
    cursor = conn.cursor()
    try:
        cursor.execute(sanitized_sql)
        rows = cursor.fetchall()
        result = [dict(row) for row in rows]
        return json.dumps({
            "status": "success",
            "executed_sql": sanitized_sql,
            "row_count": len(result),
            "data": result
        }, indent=2)
    except sqlite3.OperationalError as e:
        return json.dumps({"error": "DatabaseExecutionError", "details": str(e)}, indent=2)
    finally:
        conn.close()
    conn = get_connection()
    cursor = conn.cursor()
    try:
        cursor.execute(query)
        rows = cursor.fetchall()
        # Convert sqlite3.Row objects to dicts
        result = [dict(row) for row in rows]
        return json.dumps(result, indent=2)
    except Exception as e:
        return f"Database Error: {str(e)}"
    finally:
        conn.close()


def explain_query(query: str) -> str:
    """Returns the SQLite query execution plan to estimate complexity."""
    try:
        # We must validate it first to prevent EXPLAINing malicious writes
        sanitized_sql = validate_and_format_query(query)
    except SQLSecurityError as e:
        return json.dumps({"error": "SecurityViolation", "details": str(e)}, indent=2)

    conn = get_connection()
    cursor = conn.cursor()
    try:
        # EXPLAIN QUERY PLAN returns tabular data describing the scan/search strategy
        cursor.execute(f"EXPLAIN QUERY PLAN {sanitized_sql}")
        rows = cursor.fetchall()
        return json.dumps([dict(row) for row in rows], indent=2)
    except Exception as e:
        return json.dumps({"error": str(e)}, indent=2)
    finally:
        conn.close()