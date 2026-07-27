# Build context is project-root/ (not this folder), so this Dockerfile can
# also copy backoffice/app/ into the image: db.py imports Branch/Stock
# directly from Sagal's models (see architecture.md, Decision 2), and that
# code has to physically exist inside this image to be importable, since
# each service is its own isolated container.

FROM python:3.12-slim

WORKDIR /app

COPY product_mcp_server/requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

COPY product_mcp_server/ .

# Sibling directory to /app, matching the local dev layout db.py expects
# (product_mcp_server/ and backoffice/ as siblings on disk).
COPY backoffice/app /backoffice/app

EXPOSE 8000

CMD ["python", "server.py"]