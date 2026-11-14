FROM python:3.12-slim AS api
ENV PYTHONUNBUFFERED=1 \
    PYTHONUTF8=1 \
    PIP_NO_CACHE_DIR=1
WORKDIR /app

COPY docker/api-requirements.lock /tmp/api-requirements.lock
RUN python -m pip install -r /tmp/api-requirements.lock

COPY api/ /app/api/
COPY pipeline/common/ /app/pipeline/common/
CMD ["python", "-m", "uvicorn", "api.main:app", "--host", "0.0.0.0", "--port", "8000"]

FROM api AS watcher
COPY pipeline/monitor/requirements-lock.txt /tmp/monitor-requirements.lock
RUN python -m pip install --index-url https://download.pytorch.org/whl/cpu "torch==2.15.0" \
    && python -m pip install -r /tmp/monitor-requirements.lock \
    && python -m pip check
COPY pipeline/monitor/ /app/pipeline/monitor/
COPY docker/watcher_entrypoint.py /app/docker/watcher_entrypoint.py
ENV HF_HOME=/cache/huggingface
CMD ["python", "/app/docker/watcher_entrypoint.py"]
