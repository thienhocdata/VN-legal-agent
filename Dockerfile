FROM python:3.13-slim

ENV PYTHONDONTWRITEBYTECODE=1 PYTHONUNBUFFERED=1
WORKDIR /app
COPY pyproject.toml README.md ./
COPY app ./app
COPY scripts ./scripts
COPY source-packs ./source-packs
RUN pip install --no-cache-dir .
RUN addgroup --system legalagent && adduser --system --ingroup legalagent legalagent \
    && mkdir -p /data && chown legalagent:legalagent /data
USER legalagent
EXPOSE 8000
CMD ["uvicorn", "app.main:app", "--host", "0.0.0.0", "--port", "8000", "--proxy-headers"]
