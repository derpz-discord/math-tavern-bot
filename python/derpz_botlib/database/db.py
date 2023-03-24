import datetime
from typing import Annotated

from sqlalchemy import TIMESTAMP, MetaData, func
from sqlalchemy.orm import DeclarativeBase, mapped_column

sqlalchemy_metadata = MetaData()


class SqlAlchemyBase(DeclarativeBase):
    metadata = sqlalchemy_metadata


intpk = Annotated[int, mapped_column(primary_key=True)]
timestamp = Annotated[
    datetime.datetime,
    mapped_column(
        TIMESTAMP(timezone=True),
        nullable=False,
        server_default=func.CURRENT_TIMESTAMP(),
    ),
]
required_str = Annotated[str, mapped_column(nullable=False)]
required_int = Annotated[int, mapped_column(nullable=False)]
