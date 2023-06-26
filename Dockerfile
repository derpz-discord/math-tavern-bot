FROM python:3.10-buster

RUN apt-get update && apt-get install -y \
    libpq-dev \
    postgresql-client \
    postgresql-client-common \
    python3-pip



RUN pip install poetry==1.4.1
RUN poetry config virtualenvs.create false

COPY poetry.lock pyproject.toml /app/
WORKDIR /app

COPY . /app
RUN poetry install --no-dev --no-interaction --no-ansi

WORKDIR /app/python
ENV PYTHONPATH="/app:/app/python"
ENTRYPOINT ["python", "main.py"]



