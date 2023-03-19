"""Contains data models for the tier list plugin"""
from pydantic import BaseModel


class TierList(BaseModel):
    owner: int
    name: str