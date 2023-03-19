"""
Holds models for the book list functionality of the bot.
"""
from typing import Optional

from pydantic import BaseModel


class Author(BaseModel):
    """
    Represents an author of a book. Note that an author could have written
    multiple books.
    """

    name: str


class Publisher(BaseModel):
    name: str


class Series(BaseModel):
    """
    Represents a series of books. Note that a series could have multiple books.
    """

    name: str
    publisher: Publisher


class Book(BaseModel):
    title: str
    author: Author
    isbn: str
    series: Optional[Series]
