FROM python:3.11-slim as builder

WORKDIR /app

ENV PIP_NO_CACHE_DIR=off

COPY requirements.txt .

RUN pip wheel --no-cache-dir --wheel-dir=/app/wheels -r requirements.txt


FROM python:3.11-slim

WORKDIR /app

COPY --from=builder /app/wheels /wheels

RUN pip install --no-cache --no-index --find-links=/wheels /wheels/*

COPY download_model.py .
RUN python download_model.py

COPY . .

CMD ["uvicorn", "main:app", "--host", "0.0.0.0", "--port", "8000", "--reload"]