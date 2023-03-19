from pydantic import BaseModel


class Author(BaseModel):
    pass


class Book(BaseModel):
    title: str
    author: Author
    isbn: str
