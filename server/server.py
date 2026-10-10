from mcp.server.mcpserver import MCPServer
import db

# Initialize the MCP server using the v2 API
mcp = MCPServer("Safe-Text-to-SQL")

@mcp.resource("schema://chinook")
def get_db_schema() -> str:
    """Provides the full CREATE TABLE schema for all allowed tables."""
    schemas = []
    for table in db.list_allowed_tables():
        schemas.append(db.get_table_schema(table))
    return "\n\n".join(schemas)

@mcp.tool()
def list_tables() -> str:
    """List all database tables that the LLM is allowed to query."""
    tables = db.list_allowed_tables()
    return f"Allowed tables: {', '.join(tables)}"

@mcp.tool()
def get_table_schema(table_name: str) -> str:
    """Get the database schema (CREATE TABLE statement) for a specific table."""
    return db.get_table_schema(table_name)

@mcp.tool()
def run_query(query: str) -> str:
    """Execute a read-only SQL query against the database and return results as JSON."""
    return db.execute_read_query(query)

@mcp.tool()
def explain_query(query: str) -> str:
    """
    Get the SQLite EXPLAIN QUERY PLAN for a query without executing it.
    Use this to verify if a query uses indexes or requires expensive full table scans.
    """
    return db.explain_query(query)
    
if __name__ == "__main__":
    # Start the server on stdin/stdout
    mcp.run(transport='stdio')