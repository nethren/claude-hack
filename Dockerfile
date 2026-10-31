# Live coordinator backend for the hosted Groundline demo (Cloudflare Container).
# The API key arrives at runtime from a Cloudflare secret; it is never baked in.
FROM python:3.12-slim
WORKDIR /app
ENV PYTHONDONTWRITEBYTECODE=1 PYTHONUNBUFFERED=1 \
    COORDINATOR_MODE=live ANTHROPIC_MODEL=claude-opus-5-5
COPY requirements.lock .
RUN pip install --no-cache-dir -r requirements.lock
COPY . .
EXPOSE 8080
CMD ["python", "-m", "uvicorn", "api_fuel:app", "--host", "0.0.0.0", "--port", "8080"]
