# Updated for FastMCP implementation
FROM ghcr.io/astral-sh/uv:python3.12-bookworm-slim AS uv

# Set the working directory
WORKDIR /app

# Copy the project files to the working directory
ADD . /app

# Enable bytecode compilation
ENV UV_COMPILE_BYTECODE=1

# Copy from the cache instead of linking since it's a mounted volume
ENV UV_LINK_MODE=copy

# Sync the dependencies and lockfile
RUN uv sync --frozen --no-install-project --no-dev --no-editable

# Install the project
RUN uv sync --frozen --no-dev --no-editable

# Expose the default MCP server port
EXPOSE 8000

# Entry point for running the MCP server
ENTRYPOINT ["uv", "run", "mcp-pinecone"]
