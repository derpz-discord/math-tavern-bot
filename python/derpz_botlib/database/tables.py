import sqlalchemy
from derpz_botlib.database.db import SqlAlchemyBase
from sqlalchemy.dialects import postgresql

json_config_store = sqlalchemy.Table(
    "json_config_store",
    SqlAlchemyBase.metadata,
    sqlalchemy.Column("id", sqlalchemy.String, primary_key=True),
    sqlalchemy.Column("data", postgresql.JSONB),
)
