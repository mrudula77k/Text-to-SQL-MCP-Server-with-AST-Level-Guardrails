# Text-to-SQL-MCP-Server-with-AST-Level-Guardrails

# Governed Text-to-SQL MCP Server with AST-Level Guardrails

An enterprise-grade Model Context Protocol (MCP) server that provides governed, read-only Text-to-SQL capabilities over relational databases. Built with AST-level security validation, automated query planning checks, and an automated red-team evaluation suite.

## The Problem
Granting LLMs unrestricted SQL access to production or internal databases poses significant security risks:
- Accidental or malicious write/DDL execution (`DROP`, `DELETE`, `UPDATE`)
- Multi-statement injection attacks (`SELECT ...; DROP ...;`)
- Data exfiltration of sensitive or unauthorized tables (e.g., PII or internal salary tables)
- Resource exhaustion via runaway unbounded scans

Prompt engineering alone fails to prevent SQL injection or model hallucinations. This project enforces guardrails strictly at the database interface layer.

---

## Architecture

┌─────────────────────────────────┐
│     Custom MCP Client           │
│   Gemini 3.5 Flash-Lite         │
│  (Autonomous Tool Routing Loop) │
└────────────────┬────────────────┘
│ MCP Protocol (stdio)
▼
┌─────────────────────────────────┐
│           MCP Server            │
│                                 │
│  Tools:                         │
│   - list_tables()               │
│   - get_table_schema(table)     │
│   - run_query(sql)              │
│   - explain_query(sql)          │
│                                 │
│  Guardrail Engine (sqlglot):    │
│   - AST Parse & Single-Stmt     │
│   - Read-Only (SELECT) Clamp    │
│   - Table Allowlist Filtering   │
│   - Automatic Row Limit Clamp   │
│   - EXPLAIN Query Cost Check    │
│   - JSONL Audit Logging         │
└────────────────┬────────────────┘
│ Sanitized SQL Execution
▼
SQLite Chinook Database

---

## Evaluation Benchmark & Security Results

We evaluated the server against both an execution accuracy benchmark and a malicious red-team suite:

| Metric | Target | Result | Methodology |
|---|---|---|---|
| **Red-Team Block Rate** | 100% | **100% (8/8)** | SQL-injection, DDL drops, unauthorized table subqueries |
| **Execution Accuracy** | >90% | **100% (5/5)** | Validated against raw row result sets, not string matching |

---

## Setup & Running

### 1. Prerequisites
- Python 3.10+
- A Google Gemini API Key

### 2. Installation
```bash
git clone [https://github.com/your-username/safe-text-to-sql-mcp.git](https://github.com/your-username/safe-text-to-sql-mcp.git)
cd safe-text-to-sql-mcp
python -m venv venv
source venv/bin/activate  # On Windows: venv\Scripts\activate
pip install -r requirements.txt

### **3. Run the Evaluation Suite**
python evals/run_evals.py

###  **4. Start the Interactive Gemini Agent**
# Windows CMD
set GEMINI_API_KEY=your_key
python client/gemini_client.py

# Linux / macOS
export GEMINI_API_KEY="your_key"
python client/gemini_client.py

