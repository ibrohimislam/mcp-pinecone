# MCP-Pinecone Development Guide

## Commands
- **Install Dependencies**: `uv sync`
- **Reinstall Dependencies**: `make reinstall-deps`
- **Lint**: `make lint` or `uv run ruff check .`
- **Build**: `make build` or `uv build`
- **Publish**: `make publish` (requires PYPI_TOKEN)
- **Release**: `make release VERSION=x.x.x`
- **Run Server Locally**: `uv run mcp-pinecone`
- **Inspect Server**: `make inspect-local-server`

## Code Style
- **Imports**: Standard library first, then third-party, then local imports
- **Type Hints**: Use strict typing with Union, Optional where needed
- **Error Handling**: Use try/except blocks with specific error logging
- **Logging**: Use the logging module with appropriate levels
- **Async/Await**: Use asyncio for concurrency
- **Docstrings**: Include for all public functions/methods
- **Line Length**: 100 characters max
- **Formatting**: Follow PEP 8, enforced by Ruff
- **Naming**: snake_case for variables/functions, PascalCase for classes

## FastMCP Implementation Example

Here's an example Python script that demonstrates how to use the FastMCP implementation with mcp-pinecone:

```python
#!/usr/bin/env python3
"""
Example script showing how to run MCP-Pinecone with FastMCP implementation
"""
import sys
import logging
import uvicorn
from starlette.applications import Starlette
from starlette.routing import Mount, Host

# Import our MCP FastMCP instance
from mcp_pinecone.server import mcp

def main():
    """Run the MCP-Pinecone server with FastMCP in SSE mode"""
    try:
        logging.info("=== PINECONE MCP SERVER STARTING ===")
        logging.info(f"Python version: {sys.version}")
        
        # Create a Starlette app with the mcp.sse_app() method
        app = Starlette(routes=[Mount('/', app=mcp.sse_app())])
        app.router.routes.append(Host('mcp.acme.corp', app=mcp.sse_app()))
        
        # Run the server with uvicorn
        uvicorn.run(app, host='0.0.0.0', port=8000)
        logging.info("MCP server stopped normally")
        return 0
    
    except Exception as e:
        logging.error(f"Fatal error: {e}", exc_info=True)
        return 1

if __name__ == "__main__":
    # Configure logging
    logging.basicConfig(
        level=logging.INFO,
        format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
    )
    sys.exit(main())
```

The main differences between the Server and FastMCP implementations:

1. **Context Management**: FastMCP uses a lifespan context manager to handle initialization and cleanup
2. **Tool Registration**: Tools are defined directly with decorators on the FastMCP instance
3. **Resource Access**: Resources use the Context object to access the Pinecone client
4. **Type Definitions**: Arguments are directly typed as parameters to functions
5. **Return Values**: Functions return structured data that FastMCP converts to the appropriate MCP response format

## FastMCP Tool Definition Example

```python
@mcp.tool(description="Search pinecone for documents")
def semantic_search_tool(
    ctx: Context,
    query: str,
    top_k: int = 10,
    namespace: str = None,
    category: str = None,
    tags: list[str] = None,
    date_range: dict = None,
) -> Dict[str, Any]:
    """Search pinecone for documents"""
    try:
        # Access the pinecone client from the context
        pinecone = ctx.request_context.lifespan_context.pinecone
        
        # Use the client to perform a search
        results = pinecone.search_records(
            query=query,
            top_k=top_k,
            filter=filters,
            include_metadata=True,
            namespace=namespace,
        )
        
        # Format and return the results
        return {"success": True, "results": formatted_results}
    except Exception as e:
        return {"success": False, "error": str(e)}
```