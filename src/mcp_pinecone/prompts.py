import logging
from enum import Enum
import mcp.types as types
from mcp.server.fastmcp import Context, FastMCP
from .pinecone import PineconeClient
from datetime import datetime


logger = logging.getLogger("pinecone-mcp")


class PromptName(str, Enum):
    PINECONE_QUERY = "pinecone-query"
    PINECONE_STORE = "pinecone-store"

# With FastMCP, we don't need to predefine prompts as they are defined using decorators


def register_prompts(server: FastMCP, pinecone_client: PineconeClient):
    """Register prompts with FastMCP - this function is unused in the FastMCP version.
       All prompts are now defined directly with the @mcp.prompt decorator"""
    
    # With FastMCP, we register prompts directly using decorators
    @server.prompt(
        name=PromptName.PINECONE_QUERY,
        description="Search Pinecone index and construct an answer based on relevant pinecone documents"
    )
    def pinecone_query_prompt(
        ctx: Context,
        query: str,
    ) -> types.GetPromptResult:
        """Search Pinecone index and construct an answer based on relevant pinecone documents"""
        if not query:
            raise ValueError("Query required")

        return types.GetPromptResult(
            messages=[
                types.PromptMessage(
                    role="user",
                    content=types.TextContent(
                        type="text",
                        text="First use pinecone-stats to get a list of namespaces that might contain relevant documents. Ignore if a namespace is specified in the query",
                    ),
                ),
                types.PromptMessage(
                    role="user",
                    content=types.TextContent(
                        type="text",
                        text=f"Do a semantic search for the query: {query} with the chosen namespace",
                    ),
                ),
            ]
        )
        
    @server.prompt(
        name=PromptName.PINECONE_STORE,
        description="Store content as document in Pinecone"
    )
    def pinecone_store_prompt(
        ctx: Context,
        content: str,
        namespace: str = None,
    ) -> types.GetPromptResult:
        """Store content as document in Pinecone"""
        if not content:
            raise ValueError("Content required")
            
        metadata = {
            "date": datetime.now().isoformat(),
        }

        return types.GetPromptResult(
            messages=[
                types.PromptMessage(
                    role="user",
                    content=types.TextContent(
                        type="text",
                        text=f"The namespace is {namespace if namespace else 'not specified'}. \n"
                        "If the namespace is not specified, use pinecone-stats to find an appropriate namespace or use the default namespace.",
                    ),
                ),
                types.PromptMessage(
                    role="user",
                    content=types.TextContent(
                        type="text",
                        text=f"Based on the content, generate metadata that can be relevant to the content and used for filtering. \n"
                        "The metadata should be a dictionary with keys and values that are relevant to the content. \n"
                        f"Append the metdata to {metadata} \n",
                    ),
                ),
                types.PromptMessage(
                    role="user",
                    content=types.TextContent(
                        type="text",
                        text=f"Run the process-document tool with the content: {content} \n"
                        "Include generated metadata in the document. \n"
                        f"Store in the {namespace} if specified",
                    ),
                ),
            ]
        )


# These functions are no longer needed with FastMCP implementation
# as they are replaced by the decorated functions above


__all__ = [
    "register_prompts",
]
