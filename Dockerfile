FROM python:3.11-slim

WORKDIR /app

# Install system dependencies + Node.js (required for Qwen CLI)
RUN apt-get update && \
    apt-get install -y --no-install-recommends \
    curl \
    gnupg \
    && curl -fsSL https://deb.nodesource.com/setup_20.x | bash - \
    && apt-get install -y nodejs \
    && rm -rf /var/lib/apt/lists/*

# Install Qwen CLI globally via npm
RUN npm install -g @qwen-code/qwen-code

# Create Qwen config directory with pre-configured settings
RUN mkdir -p /root/.qwen && \
    cat > /root/.qwen/settings.json << 'SETTINGSEOF'
{
  "security": {
    "auth": {
      "selectedType": "qwen-oauth"
    }
  },
  "general": {
    "checkpointing": {
      "enabled": false
    }
  },
  "tools": {
    "approvalMode": "yolo"
  },
  "$version": 3
}
SETTINGSEOF

# Copy requirements and install Python dependencies
COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

# Copy application code
COPY . .

# Copy entrypoint script
COPY entrypoint.sh /entrypoint.sh
RUN chmod +x /entrypoint.sh

ENTRYPOINT ["/entrypoint.sh"]

# Set workspace as working directory
WORKDIR /workspace

# Expose port
EXPOSE 8000

# Health check
HEALTHCHECK --interval=30s --timeout=10s --start-period=5s --retries=3 \
    CMD curl -f http://localhost:8000/health || exit 1

# Run the application
CMD ["uvicorn", "main:app", "--host", "0.0.0.0", "--port", "8000"]
