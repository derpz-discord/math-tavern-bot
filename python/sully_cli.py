import argparse
from typing import Union

import redis
from pydantic import BaseModel


class AutoSullyRequest(BaseModel):
    guild_id: int
    channel_id: int
    message_id: int
    emoji_id: Union[int, str]


if __name__ == "__main__":
    argparser = argparse.ArgumentParser()
    argparser.add_argument("-g", type=int, required=False, default=1073267404110561353)
    argparser.add_argument("-c", type=int, required=False, default=1073267404110561356)
    # sotrue
    argparser.add_argument(
        "-e", required=False, type=Union[int, str], default=1073406460840648784
    )
    argparser.add_argument("-m", type=int)
    redis_conn = redis.from_url("redis://localhost:6379")
    args = argparser.parse_args()
    redis_conn.publish(
        "autosully",
        AutoSullyRequest(
            guild_id=args.g,
            channel_id=args.c,
            message_id=args.m,
            emoji_id=args.e,
        ).json(),
    )
