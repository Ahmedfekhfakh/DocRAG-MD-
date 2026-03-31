FROM python:3.11-slim

WORKDIR /app

# Install system deps
RUN apt-get update && apt-get install -y --no-install-recommends \
    curl build-essential \
    && rm -rf /var/lib/apt/lists/*

# Install uv
COPY --from=ghcr.io/astral-sh/uv:latest /uv /usr/local/bin/uv

# Copy project files
COPY pyproject.toml .
COPY . .

# Install PyTorch CPU-only first (avoids pulling ~3 GB of CUDA libraries)
RUN uv pip install --system torch --index-url https://download.pytorch.org/whl/cpu

# Install dependencies
RUN uv pip install --system -e .

# Make startup script executable
RUN sed -i 's/\r$//' start.sh && chmod +x start.sh

EXPOSE 8000 9001 9002

# Starts FastAPI (:8000) + MCP medical_search (:9001) + MCP citation_lookup (:9002)
CMD ["bash", "start.sh"]
