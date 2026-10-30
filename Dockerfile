FROM python:3.11-slim

ENV PYTHONDONTWRITEBYTECODE=1 \
    PYTHONUNBUFFERED=1 \
    PIP_NO_CACHE_DIR=1 \
    FASTEMBED_CACHE_DIR=/app/.cache/fastembed

WORKDIR /app

RUN apt-get update \
    && apt-get install -y --no-install-recommends libgomp1 \
    && rm -rf /var/lib/apt/lists/*

COPY requirements.txt .
RUN python -m pip install --upgrade pip \
    && python -m pip install -r requirements.txt

COPY src ./src
COPY data ./data
COPY evaluation ./evaluation
COPY scripts ./scripts
COPY reports ./reports
COPY app.py .

ENV PYTHONPATH=/app/src \
    OLLAMA_BASE_URL=http://ollama:11434 \
    MODEL_NAME=qwen3:0.6b \
    LLM_BACKEND=ollama \
    EMBEDDING_MODEL=sentence-transformers/paraphrase-multilingual-MiniLM-L12-v2 \
    MAX_CONTEXT_CHARS=6000 \
    MAX_ANSWER_TOKENS=256 \
    OLLAMA_TIMEOUT_SECONDS=300 \
    RETRIEVAL_TOP_K=5

EXPOSE 8501

CMD ["streamlit", "run", "app.py", "--server.address=0.0.0.0", "--server.port=8501"]
