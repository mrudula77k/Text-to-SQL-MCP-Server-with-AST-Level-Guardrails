import sqlglot
from sqlglot import exp
from typing import Tuple, Optional

MAX_ROW_LIMIT = 100
ALLOWED_TABLES = {
    "album", "artist", "customer", "genre", 
    "invoice", "invoiceline", "mediatype", "track"
}

class SQLSecurityError(Exception):
    """Raised when a SQL query violates security guardrails."""
    pass

def validate_and_format_query(sql: str) -> str:
    """
    Parses and enforces security constraints on SQL queries:
    1. Single statement only
    2. Strict SELECT only (no INSERT, UPDATE, DELETE, DROP, ALTER, PRAGMA)
    3. All referenced tables must be in the allowlist
    4. Enforces a maximum LIMIT clause
    """
    try:
        # Parse statements for SQLite dialect
        statements = sqlglot.parse(sql, read="sqlite")
    except Exception as e:
        raise SQLSecurityError(f"SQL Syntax Error: {str(e)}")

    if not statements or statements[0] is None:
        raise SQLSecurityError("Empty query provided.")

    if len(statements) > 1:
        raise SQLSecurityError("Multi-statement queries (semicolon chaining) are forbidden.")

    ast = statements[0]

    # Guardrail 1: Enforce pure SELECT / read-only statements
    if not isinstance(ast, exp.Select):
        raise SQLSecurityError(
            f"Write or administrative operations forbidden. Statement type '{ast.key.upper()}' is not permitted."
        )

    # Guardrail 2: AST Table Allowlist Check
    # Find all table nodes in the query tree
    referenced_tables = {
        table.name.lower() for table in ast.find_all(exp.Table) if table.name
    }
    
    unauthorized_tables = referenced_tables - ALLOWED_TABLES
    if unauthorized_tables:
        raise SQLSecurityError(
            f"Access denied to unauthorized table(s): {', '.join(unauthorized_tables)}."
        )

    # Guardrail 3: Enforce Row Limit
    limit_node = ast.args.get("limit")
    if limit_node is None:
        # Inject default limit if omitted
        ast = ast.limit(MAX_ROW_LIMIT)
    else:
        # Clamp existing limit to MAX_ROW_LIMIT
        try:
            current_limit = int(limit_node.expression.this)
            if current_limit > MAX_ROW_LIMIT or current_limit <= 0:
                ast.set("limit", exp.Limit(this=exp.Literal.number(MAX_ROW_LIMIT)))
        except (ValueError, AttributeError):
            ast.set("limit", exp.Limit(this=exp.Literal.number(MAX_ROW_LIMIT)))

    # Return sanitized SQL in SQLite dialect
    return ast.sql(dialect="sqlite")