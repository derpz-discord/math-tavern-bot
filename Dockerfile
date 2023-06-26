FROM python:3.10-buster

RUN apt-get update && apt-get install -y \
    libpq-dev \
    postgresql-client \
    postgresql-client-common


RUN pip3 install poetry==1.4.1
RUN poetry config virtualenvs.create false

WORKDIR /app

COPY poetry.lock pyproject.toml /app/

RUN poetry install --no-dev --no-interaction --no-ansi

COPY . /app

ENV PYTHONPATH="/app:/app/python:/app/python/math_tavern_bot_py"

WORKDIR /app/python
ENTRYPOINT ["python", "main.py"]
