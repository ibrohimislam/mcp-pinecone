import logging
import json
from typing import AsyncIterator
from dataclasses import dataclass
from contextlib import asynccontextmanager
from mcp.server.fastmcp import Context, FastMCP
from .pinecone import PineconeClient
from starlette.applications import Starlette
from starlette.routing import Mount, Host
import uvicorn
from .tools import register_tools
from .prompts import register_prompts

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger("pinecone-mcp")

@dataclass
class AppContext:
    """Application context for the MCP server"""
    pinecone: PineconeClient

@asynccontextmanager
async def app_lifespan(server: FastMCP) -> AsyncIterator[AppContext]:
    """
    Application lifespan for initialization and cleanup
    """
    # Initialize Pinecone client on startup
    pinecone_client = PineconeClient()
    
    logger.info("Initialized Pinecone client")
    
    try:
        yield AppContext(pinecone=pinecone_client)
    finally:
        # No cleanup needed for Pinecone client
        pass

# Create MCP server with FastMCP
mcp = FastMCP(
    "Pinecone MCP Server",
    description="MCP Server for interacting with Pinecone vector databases",
    dependencies=["pinecone-client"],
    lifespan=app_lifespan,
)

# Register tools and prompts
register_tools(mcp, None)  # PineconeClient will be available from Context
register_prompts(mcp, None)  # PineconeClient will be available from Context

@mcp.resource(
    "pinecone://vectors/{vector_id}",
    description="Get a vector by ID from Pinecone"
)
def get_vector_resource(vector_id: str) -> str:
    """Get a specific vector by ID from Pinecone"""
    try:
        # Get the pinecone client from the global instance instead
        pinecone_client = PineconeClient()
        record = pinecone_client.fetch_records([vector_id])

        if not record or "records" not in record or not record["records"]:
            return json.dumps({"error": f"Vector not found: {vector_id}"}, indent=2)

        vector_data = record["records"][0]
        metadata = vector_data.get("metadata", {})
        
        # Format output
        output = []
        if "title" in metadata:
            output.append(f"Title: {metadata['title']}")
        output.append(f"ID: {vector_data.get('id')}")

        for key, value in metadata.items():
            if key not in ["title", "text", "content_type"]:
                output.append(f"{key}: {value}")

        output.append("")

        if "text" in metadata:
            output.append(metadata["text"])

        return "\n".join(output)
    except Exception as e:
        return json.dumps({"error": str(e)}, indent=2)

@mcp.resource(
    "pinecone://vectors",
    description="List all vectors in Pinecone"
)
def list_vectors_resource() -> str:
    """List all vectors in Pinecone"""
    try:
        # Get the pinecone client from the global instance instead
        pinecone_client = PineconeClient()
        records = pinecone_client.list_records()
        
        resources = []
        for record in records.get("vectors", []):
            # If metadata is None, use empty dict
            metadata = record.get("metadata") or {}
            description = (
                metadata.get("text", "")[:100] + "..." if metadata.get("text") else ""
            )
            resources.append({
                "uri": f"pinecone://vectors/{record['id']}",
                "name": metadata.get("title", f"Vector {record['id']}"),
                "description": description,
                "metadata": metadata,
                "mimeType": metadata.get("content_type", "text/plain"),
            })
        return json.dumps(resources, indent=2)
    except Exception as e:
        return json.dumps({"error": str(e)}, indent=2)

# MCP tools will be registered in tools.py
# The main function is now simpler since FastMCP handles tool registration

def format_text_content(vector_data: dict) -> str:
    metadata = vector_data.get("metadata", {})
    output = []

    if "title" in metadata:
        output.append(f"Title: {metadata['title']}")
    output.append(f"ID: {vector_data.get('id')}")

    for key, value in metadata.items():
        if key not in ["title", "text", "content_type"]:
            output.append(f"{key}: {value}")

    output.append("")

    if "text" in metadata:
        output.append(metadata["text"])

    return "\n".join(output)


def format_binary_content(vector_data: dict) -> bytes:
    content = vector_data.get("metadata", {}).get("content", b"")
    if isinstance(content, str):
        content = content.encode("utf-8")
    return content


def run_server():
    """
    Run the MCP server with SSE transport
    This function is called from the __main__.py file
    """
    logger.info("Starting Pinecone MCP server with SSE transport...")
    app = Starlette(routes=[Mount('/', app=mcp.sse_app())])
    app.router.routes.append(Host('mcp.acme.corp', app=mcp.sse_app()))
            
    uvicorn.run(app, host='0.0.0.0', port=8000)
    logger.info("MCP server stopped normally")
    return 0

def main():
    """
    Entry point for the package
    """
    logger.info("Starting Pinecone MCP server")
    return run_server()