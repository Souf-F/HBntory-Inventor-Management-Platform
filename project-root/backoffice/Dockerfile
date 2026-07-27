# Minimal Dockerfile, written to unblock docker-compose.yml since it was
# missing (referenced but not committed). Souf/Sagal should feel free to
# adjust as the Backoffice evolves.
#
# Uses `flask run` instead of `python run.py`: run.py calls app.run(debug=True)
# with no host argument, which binds to 127.0.0.1 and would be unreachable
# from outside this container.

FROM python:3.12-slim

WORKDIR /app

COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

COPY . .

ENV FLASK_APP=app:create_app

EXPOSE 5000

CMD ["flask", "run", "--host=0.0.0.0", "--port=5000"]