#!/usr/bin/env sh
git pull
docker compose build bot
docker compose up -d bot