FROM python:3.14-slim
COPY --from=ghcr.io/astral-sh/uv:latest /uv /uvx /bin/

ADD . /app

WORKDIR /app
RUN uv sync --locked

CMD uv run manage.py makemigrations --no-input && uv run manage.py migrate --no-input && uv run gunicorn --bind 0.0.0.0:8000 --workers 4 AutoBacklog.wsgi:application