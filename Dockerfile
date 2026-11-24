# Image Cloud Run : app web + agent + index RAG « cuit » (embeddings Vertex).
# Ni Ollama ni serveur Chroma : l'index persistant est embarqué dans l'image.
FROM python:3.12-slim
WORKDIR /app
ENV PYTHONPATH=/app/src PYTHONUTF8=1 PIP_NO_CACHE_DIR=1 \
    EMBED_PROVIDER=vertex CHROMA_MODE=persistent CHROMA_PATH=/app/chroma_index \
    LLM_PROVIDER=google_genai LLM_MODEL=gemini-3.8-flash \
    GOOGLE_GENAI_USE_VERTEXAI=true GOOGLE_CLOUD_LOCATION=global
COPY requirements.txt requirements-cloud.txt ./
RUN pip install -r requirements.txt -r requirements-cloud.txt fastapi uvicorn google-genai
COPY src/ ./src/
COPY web/ ./web/
COPY chroma_index/ ./chroma_index/
CMD exec uvicorn web.app:app --host 0.0.0.0 --port ${PORT:-8080}
