from sqlalchemy import text

from app.db import Base, engine
import app.models  # noqa: F401


def main():
    with engine.begin() as conn:
        conn.execute(text("CREATE EXTENSION IF NOT EXISTS vector"))
    Base.metadata.create_all(engine)
    print("DB ready.")


if __name__ == "__main__":
    main()