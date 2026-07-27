FROM python:3.11-slim

ENV PYTHONDONTWRITEBYTECODE=1
ENV PYTHONUNBUFFERED=1
ENV HBN_PRODUCTS_PORT=5000

WORKDIR /app

COPY app.py /app/app.py
COPY data /app/data

RUN useradd --create-home --shell /usr/sbin/nologin appuser
USER appuser

EXPOSE 5000

CMD ["python", "app.py"]
