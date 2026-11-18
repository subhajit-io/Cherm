FROM python:3.11-slim

WORKDIR /app

# Install system dependencies
RUN apt-get update && apt-get install -y --no-install-recommends \
    git \
    curl \
    && rm -rf /var/lib/apt/lists/*

# Install FastMCP and analysis dependencies
RUN pip install --no-cache-dir \
    fastmcp \
    uvicorn \
    pydantic

# Copy MCP server code
COPY cherm_mcp.py /app/

# Expose Streamable HTTP / SSE port
EXPOSE 8000

# Run FastMCP server via SSE transport on 0.0.0.0
CMD ["python", "-m", "fastmcp", "run", "cherm_mcp.py", "--transport", "sse", "--host", "0.0.0.0", "--port", "8000"]

