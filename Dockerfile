FROM python:3.10-buster

RUN sudo apt-get update && sudo apt-get install -y \
    libpq-dev \
    postgresql-client \
    postgresql-client-common \
    python3-pip

COPY . /app
WORKDIR /app

RUN pip install pipx
RUN pipx install poetry

RUN poetry config virtualenvs.create false
RUN poetry install --no-dev

WORKDIR /app/python
ENV PYTHONPATH="."
ENTRYPOINT ["python", "main.py"]k



