import json
from datetime import datetime
from pathlib import Path

# Save logs alongside the database
LOG_FILE = Path(__file__).resolve().parent.parent / "data" / "audit_log.jsonl"

def log_query(original_query: str, status: str, details: str = "", row_count: int = 0):
    """Appends a query execution event to the JSONL audit log."""
    log_entry = {
        "timestamp": datetime.utcnow().isoformat() + "Z",
        "query": original_query,
        "status": status,
        "details": details,
        "row_count": row_count
    }
    
    with open(LOG_FILE, "a", encoding="utf-8") as f:
        f.write(json.dumps(log_entry) + "\n")