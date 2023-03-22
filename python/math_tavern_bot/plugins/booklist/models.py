"""
Holds models for the book list functionality of the bot.
"""
from typing import Optional

import disnake
import sqlalchemy
from derpz_botlib.database.db import SqlAlchemyBase
from pydantic import BaseModel, Field, validator


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
    edition: int
    series: Optional[Series]


class BookInDb(SqlAlchemyBase):
    __tablename__ = "books"

    id = sqlalchemy.Column(sqlalchemy.Integer, primary_key=True)
    server = sqlalchemy.Column(sqlalchemy.BigInteger, nullable=False)
    title = sqlalchemy.Column(sqlalchemy.String, nullable=False)
    author = sqlalchemy.Column(sqlalchemy.String, nullable=False)
    isbn = sqlalchemy.Column(sqlalchemy.String, nullable=False)
    subject = sqlalchemy.Column(sqlalchemy.String)
    s3_key = sqlalchemy.Column(sqlalchemy.String, nullable=False)

    uploaded_at = sqlalchemy.Column(sqlalchemy.DateTime, server_default=sqlalchemy.func.now())
    # TODO: Audit log
    # TODO: Allow admins to modify


def check_isbn10(isbn: str) -> bool:
    """
    Checks if the ISBN is valid
    :param isbn: The ISBN to check
    :return: True if valid, False otherwise
    """
    if len(isbn) != 10:
        return False
    if not isbn.isnumeric():
        return False
    # See Gallian Chapter 0 exercise 45
    mult = list(range(10, 0, -1))
    total = 0
    for i in range(10):
        total += int(isbn[i]) * mult[i]
    return total % 11 == 0


def check_isbn13(isbn: str) -> bool:
    """
    Checks if the ISBN is valid
    :param isbn: The ISBN to check
    :return: True if valid, False otherwise
    """
    if len(isbn) != 13:
        return False
    if not isbn.isnumeric():
        return False
    # check first 3 digits
    if not isbn.startswith("978") and not isbn.startswith("979"):
        return False
    # truncate and check the isbn10
    return check_isbn10(isbn[3:])


class BookMetadata(BaseModel):
    # TODO: Move this into models.py
    download_url: str
    title: str = Field(..., min_length=1)
    author: str = Field(..., min_length=1)
    # TODO: Isbn validation
    # TODO: Convert everything to ISBN13
    isbn: str
    subject: str = Field(..., min_length=1)

    def to_embed(self) -> disnake.Embed:
        embed = disnake.Embed(title="Book Metadata")
        embed.add_field(name="Title", value=self.title, inline=False)
        embed.add_field(name="Author", value=self.author, inline=False)
        embed.add_field(name="ISBN", value=self.isbn, inline=False)
        embed.add_field(name="Subject", value=self.subject, inline=False)
        return embed

    @validator("isbn")
    def isbn_is_valid(cls, isbn: str) -> str:
        isbn = isbn.strip()
        isbn = isbn.replace("-", "")
        if not check_isbn10(isbn) and not check_isbn13(isbn):
            raise ValueError("Invalid ISBN")
        return isbn
