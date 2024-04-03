from pydantic import BaseSettings


class Settings(BaseSettings):
    app_name: str = "toDos FastAPI"
    SQLALCHEMY_PGRES_DATABASE_URL: str = "postgresql://mrayhbnk:7RqHvrjBbM6LL4KO0Zq6EGdH7mdcsyUE@berry.db.elephantsql.com/mrayhbnk"
    SECRET_KEY = "KlgH6AzYDeZeGwD288to79I3vTHT8wp7"
    ALGORITHM = "HS256"
    isMongoTrue: bool = False
