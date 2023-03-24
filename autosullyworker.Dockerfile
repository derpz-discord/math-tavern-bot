FROM python:3.10-buster

RUN apt-get update && apt-get install -y python3-pip

RUN pip3 install disnake aioredis python-dotenv pydantic

COPY ./python/sully_worker.py /app/sully_worker.py

WORKDIR /app

ENTRYPOINT ["python3", "sully_worker.py"]