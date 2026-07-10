# Gita Wisdom API — deployed as a Hugging Face Docker Space.
# Python 3.11 is pinned because torch/sentence-transformers ship stable wheels for it.
FROM python:3.11-slim

# Hugging Face Spaces run the container as a non-root user with UID 1000.
# Create that user so the model cache and app files are writable at runtime.
RUN useradd -m -u 1000 user
USER user
ENV HOME=/home/user \
    PATH=/home/user/.local/bin:$PATH \
    HF_HOME=/home/user/.cache/huggingface \
    PYTHONUNBUFFERED=1

WORKDIR /app

# Install CPU-only PyTorch first so sentence-transformers doesn't pull the
# ~2GB CUDA build we don't need on a free CPU Space.
RUN pip install --no-cache-dir --user torch --index-url https://download.pytorch.org/whl/cpu

# Install the rest of the Python dependencies.
COPY --chown=user requirements.txt .
RUN pip install --no-cache-dir --user -r requirements.txt

# Copy the application code (server.py, config.py, data/, etc.).
COPY --chown=user . .

# Bake the embedding model into the image so the first request is instant and
# doesn't depend on a runtime download. Must match retrieval.py's MODEL_NAME.
RUN python -c "from sentence_transformers import SentenceTransformer; SentenceTransformer('all-MiniLM-L6-v2')"

# HF Spaces route external traffic to port 7860.
EXPOSE 7860
CMD ["uvicorn", "server:app", "--host", "0.0.0.0", "--port", "7860"]
