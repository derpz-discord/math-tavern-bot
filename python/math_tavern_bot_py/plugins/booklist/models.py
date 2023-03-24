"""
Holds models for the book list functionality of the bot.
"""

import disnake
from derpz_botlib.database.db import (SqlAlchemyBase, intpk, required_int,
                                      required_str, tz_aware_timestamp)
from pydantic import BaseModel, Field, validator
from sqlalchemy import VARCHAR
from sqlalchemy.orm import Mapped, mapped_column


class BookInDb(SqlAlchemyBase):
    __tablename__ = "books"

    id: Mapped[intpk]
    server: Mapped[required_int]
    uploaded_by: Mapped[required_int]
    title: Mapped[required_str]
    author: Mapped[required_str]
    isbn: Mapped[str] = mapped_column(VARCHAR(13), nullable=False)
    subject: Mapped[str]
    s3_key: Mapped[required_str]

    uploaded_at: Mapped[tz_aware_timestamp]
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
