import json
import sqlite3
import sys
from pathlib import Path

# Add project root to path for imports
ROOT_DIR = Path(__file__).resolve().parent.parent
sys.path.append(str(ROOT_DIR / "server"))

from guardrails import validate_and_format_query, SQLSecurityError
import db

def normalize_row(row):
    """Normalize row values for robust comparison regardless of type drift."""
    return tuple(round(x, 2) if isinstance(x, float) else x for x in row)

def execute_raw(sql: str):
    conn = db.get_connection()
    cursor = conn.cursor()
    cursor.execute(sql)
    rows = cursor.fetchall()
    conn.close()
    return [normalize_row(tuple(r)) for r in rows]

def run_redteam_evals():
    file_path = ROOT_DIR / "evals" / "redteam_set.json"
    with open(file_path, "r", encoding="utf-8") as f:
        cases = json.load(f)

    blocked = 0
    total = len(cases)

    print(f"\n--- Running Red-Team Suite ({total} tests) ---")
    for case in cases:
        query = case["raw_sql"]
        try:
            validate_and_format_query(query)
            print(f"[FAIL] Did not block: {case['id']} - {case['prompt']}")
        except SQLSecurityError:
            blocked += 1
            print(f"[PASS] Successfully blocked: {case['id']}")

    rate = (blocked / total) * 100
    print(f"Red-Team Block Rate: {blocked}/{total} ({rate:.1f}%)\n")
    return rate

def run_reference_correctness_evals():
    file_path = ROOT_DIR / "evals" / "correctness_set.json"
    with open(file_path, "r", encoding="utf-8") as f:
        cases = json.load(f)

    passed = 0
    total = len(cases)

    print(f"--- Running Baseline Query Validation ({total} tests) ---")
    for case in cases:
        ref_sql = case["reference_sql"]
        try:
            # Check if reference queries pass security guardrails
            sanitized = validate_and_format_query(ref_sql)
            results = execute_raw(sanitized)
            if results is not None:
                passed += 1
                print(f"[PASS] Reference validated: {case['id']}")
            else:
                print(f"[FAIL] Returned None: {case['id']}")
        except Exception as e:
            print(f"[FAIL] Reference query failed: {case['id']} - {str(e)}")

    rate = (passed / total) * 100
    print(f"Reference Integrity: {passed}/{total} ({rate:.1f}%)\n")
    return rate

if __name__ == "__main__":
    run_redteam_evals()
    run_reference_correctness_evals()