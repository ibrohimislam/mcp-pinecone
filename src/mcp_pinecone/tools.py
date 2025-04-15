import json
import logging
from typing import Dict, Any, TypedDict, List, Optional
from enum import Enum
from mcp.server.fastmcp import FastMCP, Context
from .pinecone import PineconeClient, PineconeRecord
from .chunking import create_chunker


logger = logging.getLogger("pinecone-mcp")


class ToolName(str, Enum):
    SEMANTIC_SEARCH = "semantic-search"
    READ_DOCUMENT = "read-document"
    PROCESS_DOCUMENT = "process-document"
    LIST_DOCUMENTS = "list-documents"
    PINECONE_STATS = "pinecone-stats"


def register_tools(mcp: FastMCP, _: PineconeClient = None):
    """
    Register tools with the FastMCP instance
    The pinecone client will be accessed from the Context
    """
    @mcp.tool(name=ToolName.SEMANTIC_SEARCH, description="Search pinecone for documents")
    def semantic_search_tool(
        ctx: Context,
        query: str,
        top_k: int = 10,
        namespace: Optional[str] = None,
        category: Optional[str] = None,
        tags: Optional[List[str]] = None,
        date_range: Optional[Dict[str, str]] = None,
    ) -> Dict[str, Any]:
        """Search pinecone for documents"""
        try:
            pinecone_client = ctx.request_context.lifespan_context.pinecone
            filters = {}
            
            if category:
                filters["category"] = category
            if tags:
                filters["tags"] = {"$in": tags}
            if date_range and "start" in date_range and "end" in date_range:
                filters["date"] = {
                    "$gte": date_range["start"],
                    "$lte": date_range["end"],
                }
            
            results = pinecone_client.search_records(
                query=query,
                top_k=top_k,
                filter=filters,
                include_metadata=True,
                namespace=namespace,
            )
            
            matches = results.get("matches", [])

            # Format results with rich context
            formatted_text = "Retrieved Contexts:\n\n"
            for i, match in enumerate(matches, 1):
                metadata = match.get("metadata", {})
                formatted_text += f"Result {i} | Similarity: {match['score']:.3f} | Document ID: {match['id']}\n"
                formatted_text += f"{metadata.get('text', '').strip()}\n"
                formatted_text += "-" * 10 + "\n\n"
                
            return {"type": "text", "text": formatted_text}
        except Exception as e:
            logger.error(f"Error in semantic search: {e}")
            return {"type": "text", "text": f"Error: {str(e)}"}
            
    @mcp.tool(name=ToolName.PINECONE_STATS, description="Get stats about the Pinecone index specified in this server")
    def pinecone_stats_tool(ctx: Context) -> Dict[str, Any]:
        """Get stats about the Pinecone index specified in this server"""
        try:
            pinecone_client = ctx.request_context.lifespan_context.pinecone
            stats = pinecone_client.stats()
            return {"type": "text", "text": json.dumps(stats)}
        except Exception as e:
            logger.error(f"Error getting stats: {e}")
            return {"type": "text", "text": f"Error: {str(e)}"}
            
    @mcp.tool(name=ToolName.READ_DOCUMENT, description="Read a document from pinecone")
    def read_document_tool(
        ctx: Context,
        document_id: str,
        namespace: Optional[str] = None,
    ) -> Dict[str, Any]:
        """Read a document from pinecone"""
        try:
            pinecone_client = ctx.request_context.lifespan_context.pinecone
            record = pinecone_client.fetch_records([document_id], namespace=namespace)
            
            # Get the vector data for this document
            vector = record.vectors.get(document_id)
            if not vector:
                return {"type": "text", "text": f"Document {document_id} not found"}
                
            # Get metadata from the vector
            metadata = vector.metadata if hasattr(vector, "metadata") else {}
            
            # Format the document content
            formatted_content = []
            formatted_content.append(f"Document ID: {document_id}")
            formatted_content.append("")  # Empty line for spacing
            
            if metadata:
                formatted_content.append("Metadata:")
                for key, value in metadata.items():
                    formatted_content.append(f"{key}: {value}")
                    
            return {"type": "text", "text": "\n".join(formatted_content)}
        except Exception as e:
            logger.error(f"Error reading document: {e}")
            return {"type": "text", "text": f"Error: {str(e)}"}
            
    @mcp.tool(name=ToolName.PROCESS_DOCUMENT, description="Process a document. This will optionally chunk, then embed, and upsert the document into pinecone.")
    def process_document_tool(
        ctx: Context,
        document_id: str,
        text: str,
        metadata: Dict[str, Any],
        namespace: Optional[str] = None,
    ) -> Dict[str, Any]:
        """Process a document by chunking, embedding, and upserting it into pinecone"""
        try:
            pinecone_client = ctx.request_context.lifespan_context.pinecone
            chunker = create_chunker(chunk_type="smart")
            chunks = chunker.chunk_document(document_id, text, metadata)
            
            embedded_chunks = []
            for chunk in chunks:
                content = chunk.content
                chunk_id = chunk.id
                chunk_metadata = chunk.metadata
                
                if not content or not chunk_id:
                    logger.warning(f"Skipping invalid chunk: {chunk}")
                    continue
                    
                embedding = pinecone_client.generate_embeddings(content)
                record = PineconeRecord(
                    id=chunk_id,
                    embedding=embedding,
                    text=content,
                    metadata=chunk_metadata,
                )
                embedded_chunks.append(record)
                
            if not embedded_chunks:
                return {"type": "text", "text": "Error: No embedded chunks found"}
                
            pinecone_client.upsert_records(embedded_chunks, namespace=namespace)
            
            return {
                "type": "text",
                "text": f"Successfully processed document. The document ID is {document_id}"
            }
        except Exception as e:
            logger.error(f"Error processing document: {e}")
            return {"type": "text", "text": f"Error: {str(e)}"}
            
    @mcp.tool(name=ToolName.LIST_DOCUMENTS, description="List all documents in the knowledge base by namespace")
    def list_documents_tool(
        ctx: Context,
        namespace: str,
    ) -> Dict[str, Any]:
        """List all documents in the knowledge base by namespace"""
        try:
            pinecone_client = ctx.request_context.lifespan_context.pinecone
            results = pinecone_client.list_records(namespace=namespace)
            return {"type": "text", "text": json.dumps(results)}
        except Exception as e:
            logger.error(f"Error listing documents: {e}")
            return {"type": "text", "text": f"Error: {str(e)}"}


class EmbeddingResult(TypedDict):
    embedded_chunks: list[PineconeRecord]
    total_embedded: int


def upsert_documents(
    records: list[PineconeRecord],
    pinecone_client: PineconeClient,
    namespace: str | None = None,
) -> Dict[str, Any]:
    """
    Upsert a list of Pinecone records into the knowledge base.
    """
    result = pinecone_client.upsert_records(records, namespace=namespace)
    return result


__all__ = [
    "register_tools",
]
